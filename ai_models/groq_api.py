from typing import TypeVar, Type, Any, Optional, List, Dict, Union, Literal, Callable
from pydantic import BaseModel, Field
import groq
from functools import wraps
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
def get_client():
    return groq.Groq(
        api_key=os.getenv("GROQ_API_KEY", "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")
    )

client = get_client()

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

def handle_groq_errors(func):
    """Decorator to handle Groq API errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except groq.error.APIError as e:
            raise Exception(f"Groq API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
    return wrapper

def _format_completion_response_json(response: Dict[str, Any], total_tokens: int) -> str:
    """Format the completion response as JSON"""
    # Calculate cost based on tokens used (using Groq's pricing)
    # Groq LLaMA 3 8B: $0.10/1M input tokens, $0.20/1M output tokens
    # This is much cheaper than Claude
    cost = (total_tokens * 0.0000002)  # Simplified cost calculation

    return json.dumps({
        "data": response,
        "cost": cost,
        "total_tokens": total_tokens
    })

@handle_groq_errors
def structured_chat_completion(
    messages: list[dict[str, str]],
    output_model: Type[T],
    model: str = "llama3-8b-8192", # Usando o llama3-8b como padrão
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Tool]] = None,
    tool_handler: Optional[ToolHandler] = None,
    **kwargs: Any
) -> T:
    """
    Make a chat completion request to Groq and parse the response.
    Supports tool calls and their execution through a provided tool handler.
    """
    working_messages = []
    for msg in messages:
        if msg["role"] == "system":
            working_messages.append({"role": "system", "content": msg["content"]})
        elif msg["role"] == "user":
            working_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            working_messages.append({"role": "assistant", "content": msg["content"]})
        elif msg["role"] == "tool":
            # Convert tool responses to assistant messages for Groq
            working_messages.append({"role": "assistant", "content": f"Tool response: {msg['content']}"})
    
    # Configurar as funções para a API do Groq, se fornecidas
    function_call = "auto" if tools else None
    functions = [tool.function.model_dump() for tool in tools] if tools else None
    
    try:
        # Fazer a chamada principal à API
        chat_completion = client.chat.completions.create(
            model=model,
            messages=working_messages,
            temperature=temperature,
            max_tokens=max_tokens or 1024,
            tools=functions,
            tool_choice=function_call,
            **kwargs
        )
        
        # Verificar se há chamadas de ferramenta
        if tools and tool_handler and chat_completion.choices[0].message.tool_calls:
            tool_calls = chat_completion.choices[0].message.tool_calls
            
            # Adicionar a mensagem do assistente com as chamadas de ferramentas
            working_messages.append(chat_completion.choices[0].message.model_dump())
            
            # Processar cada chamada de ferramenta
            for tool_call in tool_calls:
                try:
                    # Extrair nome da ferramenta e argumentos
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Executar a ferramenta
                    result = tool_handler({"name": function_name}, function_args)
                    
                    # Adicionar o resultado à lista de mensagens
                    working_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                except Exception as e:
                    # Se houver erro na execução da ferramenta, registrar o erro
                    working_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {str(e)}"
                    })
            
            # Fazer uma nova chamada com os resultados das ferramentas
            final_response = client.chat.completions.create(
                model=model,
                messages=working_messages,
                temperature=temperature,
                max_tokens=max_tokens or 1024
            )
            
            # Calcular tokens totais (estimativa)
            total_tokens = final_response.usage.completion_tokens + final_response.usage.prompt_tokens
            
            # Retornar a resposta final formatada
            return _format_completion_response_json(
                final_response.choices[0].message.content,
                total_tokens
            )
        
        # Se não houver ferramentas, retornar a resposta direta
        # Calcular tokens totais
        total_tokens = chat_completion.usage.completion_tokens + chat_completion.usage.prompt_tokens
        
        # Retornar a resposta formatada
        return _format_completion_response_json(
            chat_completion.choices[0].message.content,
            total_tokens
        )
        
    except Exception as e:
        raise Exception(f"Error calling Groq API: {str(e)}") 