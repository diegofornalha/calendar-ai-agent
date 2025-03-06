from typing import TypeVar, Type, Any, Optional, List, Dict, Union, Literal, Callable
from pydantic import BaseModel, Field
import anthropic
from functools import wraps
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verificar se estamos rodando no Streamlit Cloud
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_RUNTIME_ENV') == 'cloud'

# Initialize Anthropic client
# Usar uma função para inicializar o cliente para permitir atualizações posteriores
def get_client():
    """
    Obtém um cliente Anthropic, com tratamento para diferentes versões e ambientes.
    """
    # Configuração básica para qualquer ambiente
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Se não há chave API definida, não tentar criar o cliente
    if not api_key:
        print("Chave API Anthropic não definida")
        return None
    
    try:
        # Tentar criar o cliente com a abordagem padrão
        return anthropic.Anthropic(api_key=api_key)
    except TypeError as e:
        # Se houver erro de tipo, pode ser incompatibilidade de assinatura
        print(f"Erro ao criar cliente com assinatura padrão: {str(e)}")
        
        # Tentar métodos alternativos com base no erro específico
        if "proxies" in str(e) or "unexpected keyword" in str(e):
            try:
                # Tentar criar com a classe Client em vez de Anthropic
                return anthropic.Client(api_key=api_key)
            except Exception as inner_e:
                print(f"Erro ao criar cliente alternativo: {str(inner_e)}")
                if IS_STREAMLIT_CLOUD:
                    return None
                else:
                    raise
        
        # Se estamos no cloud, falhar silenciosamente
        if IS_STREAMLIT_CLOUD:
            print(f"Erro ao criar cliente Anthropic no ambiente cloud: {str(e)}")
            return None
        else:
            # Em ambiente local, propagar o erro para diagnóstico
            raise
    except Exception as e:
        # Lidar com outros erros
        print(f"Erro ao criar cliente Anthropic: {str(e)}")
        if IS_STREAMLIT_CLOUD:
            return None
        else:
            raise

# Inicializar o cliente com tratamento de erro
try:
    client = get_client()
    if client is None and IS_STREAMLIT_CLOUD:
        print("Cliente Anthropic não disponível no ambiente cloud. Usando fallback para Groq.")
except Exception as e:
    print(f"Erro ao inicializar cliente Anthropic: {str(e)}")
    client = None

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

# Type for tool handler function
ToolHandler = Callable[[Dict[str, Any], Dict[str, Any]], Any]

class FunctionParameters(BaseModel):
    type: Literal["object"] = "object"
    properties: Dict[str, Dict[str, Any]]
    required: List[str]
    additionalProperties: bool = False

class Function(BaseModel):
    name: str
    description: str
    parameters: FunctionParameters
    strict: bool = True

class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: Function

def handle_anthropic_errors(func):
    """Decorator to handle Anthropic API errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except anthropic.APIError as e:
            raise Exception(f"Anthropic API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    return wrapper

def _format_completion_response_json(response: Dict[str, Any], total_tokens: int) -> str:
    """Format the completion response as JSON"""
    # Calculate cost based on tokens used (using Anthropic's pricing)
    # Claude 3 Haiku: $0.25/1M input tokens, $1.25/1M output tokens
    # Claude 3 Sonnet: $3/1M input tokens, $15/1M output tokens
    cost = (total_tokens * 0.000003)  # Simplified cost calculation for Sonnet

    return json.dumps({
        "data": response,
        "cost": cost,
        "total_tokens": total_tokens
    })

@handle_anthropic_errors
def structured_chat_completion(
    messages: list[dict[str, str]],
    output_model: Type[T],
    model: str = "claude-3-sonnet-20250219",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Tool]] = None,
    tool_handler: Optional[ToolHandler] = None,
    **kwargs: Any
) -> T:
    """
    Make a chat completion request to Anthropic and parse the response.
    Supports tool calls and their execution through a provided tool handler.
    """
    # Verificar se o cliente está disponível
    if client is None:
        if IS_STREAMLIT_CLOUD:
            # No ambiente cloud, retornar uma resposta simplificada
            error_msg = "API Anthropic não está disponível no ambiente cloud. Por favor, use a API Groq."
            return _format_completion_response_json(
                {"message": error_msg},
                0  # Sem tokens usados
            )
        else:
            # Em ambiente local, informar que o cliente não foi inicializado corretamente
            raise Exception("Cliente Anthropic não está inicializado. Verifique sua chave de API.")
    
    working_messages = []
    for msg in messages:
        if msg["role"] == "system":
            working_messages.append({"role": "system", "content": msg["content"]})
        elif msg["role"] == "user":
            working_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            working_messages.append({"role": "assistant", "content": msg["content"]})
        elif msg["role"] == "tool":
            # Convert tool responses to assistant messages for Anthropic
            working_messages.append({"role": "assistant", "content": f"Tool response: {msg['content']}"})

    # Create the message batch for parallel processing
    requests = []
    
    # Add the main completion request
    requests.append({
        "custom_id": "main_completion",
        "params": {
            "model": model,
            "max_tokens": max_tokens or 1000,
            "messages": working_messages,
        }
    })

    # If tools are provided, add a request to check if we need to use them
    if tools:
        tool_messages = working_messages.copy()
        tool_messages.append({
            "role": "system",
            "content": "You have access to the following tools: " + 
                      ", ".join([tool.function.name for tool in tools]) +
                      ". If you need to use any of these tools, respond with the tool name and arguments in JSON format."
        })
        
        requests.append({
            "custom_id": "tool_check",
            "params": {
                "model": "claude-3-haiku-20241022",  # Use faster model for tool checking
                "max_tokens": 100,
                "messages": tool_messages,
            }
        })

    # Make the batch request
    message_batch = client.beta.messages.batches.create(requests=requests)

    # Process the responses
    main_response = None
    tool_response = None
    
    for response in message_batch.responses:
        if response.custom_id == "main_completion":
            main_response = response.message
        elif response.custom_id == "tool_check":
            tool_response = response.message

    # If tool usage is detected, handle it
    if tool_response and tool_handler and "tool" in tool_response.content.lower():
        try:
            # Parse the tool call from the response
            tool_call = json.loads(tool_response.content)
            result = tool_handler(tool_call, tool_call.get("arguments", {}))
            
            # Add the tool result to messages and make another completion
            working_messages.append({
                "role": "assistant",
                "content": f"Tool result: {json.dumps(result)}"
            })
            
            final_response = client.messages.create(
                model=model,
                max_tokens=max_tokens or 1000,
                messages=working_messages
            )
            
            return _format_completion_response_json(
                final_response.content,
                final_response.usage.input_tokens + final_response.usage.output_tokens
            )
        except Exception as e:
            # If there's an error handling the tool, log it and continue with the main response
            print(f"Error handling tool: {str(e)}")
    
    # If no tools were used or needed, return the main response
    return _format_completion_response_json(
        main_response.content,
        main_response.usage.input_tokens + main_response.usage.output_tokens
    ) 