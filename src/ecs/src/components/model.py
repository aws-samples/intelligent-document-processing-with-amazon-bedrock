"""
Copyright © Amazon.com and Affiliates
"""

from typing import Dict

MODEL_IDS = {
    # AI21 Labs Models
    "Jamba Instruct": "ai21.jamba-instruct-v1:0",
    "Jurassic 2 Mid": "ai21.j2-mid-v1",
    "Jurassic 2 Ultra": "ai21.j2-ultra-v1",
    "Jamba 1.5 Large": "ai21.jamba-1-5-large-v1:0",
    "Jamba 1.5 Mini": "ai21.jamba-1-5-mini-v1:0",
    # Amazon Models
    "Nova Micro": "amazon.nova-micro-v1:0",
    "Nova Lite": "amazon.nova-lite-v1:0",
    "Nova Pro": "amazon.nova-pro-v1:0",
    "Nova Premier": "amazon.nova-premier-v1:0",
    "Titan Text Express": "amazon.titan-text-express-v1",
    "Titan Text Lite": "amazon.titan-text-lite-v1",
    "Titan Text Premier": "amazon.titan-text-premier-v1:0",
    "Titan Embeddings Text": "amazon.titan-embed-text-v1",
    "Titan Embedding Text v2": "amazon.titan-embed-text-v2:0",
    "Titan Multimodal Embeddings": "amazon.titan-embed-image-v1",
    "Titan Image Generator v1": "amazon.titan-image-generator-v1",
    "Titan Image Generator v2": "amazon.titan-image-generator-v2:0",
    "Amazon Rerank": "amazon.rerank-v1:0",
    # Anthropic Models
    "Claude Instant": "anthropic.claude-instant-v1",
    "Claude 2.0": "anthropic.claude-v2",
    "Claude 2.1": "anthropic.claude-v2:1",
    "Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "Claude 3 Opus": "anthropic.claude-3-opus-20240229-v1:0",
    "Claude 3.5 Haiku": "anthropic.claude-3-5-haiku-20241022-v1:0",
    "Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "Claude 3.5 Sonnet (V2)": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "Claude 3.7 Sonnet": "anthropic.claude-3-7-sonnet-20250219-v1:0",
    "Claude 4 Sonnet": "anthropic.claude-sonnet-4-20250514-v1:0",
    "Claude 4.5 Sonnet": "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "Claude 4 Opus": "anthropic.claude-opus-4-20250514-v1:0",
    "Claude 4.1 Opus": "anthropic.claude-opus-4-1-20250805-v1:0",
    # DeepSeek Models
    "DeepSeek-R1": "deepseek.r1-v1:0",
    "DeepSeek 3.1": "deepseek.v3-v1:0",
    # Cohere Models
    "Command": "cohere.command-text-v14",
    "Command Light": "cohere.command-light-text-v14",
    "Command R": "cohere.command-r-v1:0",
    "Command R+": "cohere.command-r-plus-v1:0",
    "Embed English": "cohere.embed-english-v3",
    "Embed Multilingual": "cohere.embed-multilingual-v3",
    "Cohere Rerank 3.5": "cohere.rerank-v3-5:0",
    # Meta Models
    "Llama 2 13B": "meta.llama2-13b-chat-v1",
    "Llama 2 70B": "meta.llama2-70b-chat-v1",
    "Llama 3 8B": "meta.llama3-8b-instruct-v1:0",
    "Llama 3 70B": "meta.llama3-70b-instruct-v1:0",
    "Llama 3.1 8B": "meta.llama3-1-8b-instruct-v1:0",
    "Llama 3.1 70B": "meta.llama3-1-70b-instruct-v1:0",
    "Llama 3.1 405B": "meta.llama3-1-405b-instruct-v1:0",
    "Llama 3.2 1B": "meta.llama3-2-1b-instruct-v1:0",
    "Llama 3.2 3B": "meta.llama3-2-3b-instruct-v1:0",
    "Llama 3.2 11B": "meta.llama3-2-11b-instruct-v1:0",
    "Llama 3.2 90B": "meta.llama3-2-90b-instruct-v1:0",
    "Llama 4 Scout": "meta.llama4-scout-17b-instruct-v1:0",
    "Llama 4 Maverick": "meta.llama4-maverick-17b-instruct-v1:0",
    # Mistral AI Models
    "Pixtral Large": "mistral.pixtral-large-2502-v1:0",
    "Mistral 7B": "mistral.mistral-7b-instruct-v0:2",
    "Mixtral 8x7B": "mistral.mixtral-8x7b-instruct-v0:1",
    "Mistral Large": "mistral.mistral-large-2402-v1:0",
    "Mistral Large 2": "mistral.mistral-large-2407-v1:0",
    "Mistral Small": "mistral.mistral-small-2402-v1:0",
    # OpenAI Models
    "GPT OSS-120B": "openai.gpt-oss-120b-1:0",
    "GPT OSS-20B": "openai.gpt-oss-20b-1:0",
    # Qwen Models
    "Qwen 3 Coder 30B-A3B": "qwen.qwen3-coder-30b-a3b-v1:",
    "Qwen 3 32B": "qwen.qwen3-32b-v1:0",
    "Qwen 3 235B-A22B": "qwen.qwen3-235b-a22b-2507-v1:0",
    "Qwen 3 Coder 480B-A35B": "qwen.qwen3-coder-480b-a35b-v1:0",
    # Writer Models
    "Palmyra X4": "writer.palmyra-x4-v1:0",
    "Palmyra X5": "writer.palmyra-x5-v1:0",
}


def get_model_names(bedrock_model_ids: list[str]) -> Dict[str, str]:
    """
    Get dictionary of available models and their IDs filtered by bedrock_model_ids
    """
    # Create a reverse mapping from model_id to name
    id_to_name = {model_id: name for name, model_id in MODEL_IDS.items()}

    # Create new dictionary ordered by bedrock_model_ids sequence
    result = {}
    for model_id in bedrock_model_ids:
        if model_id.startswith(("global.", "us.", "eu.")):
            base_id = model_id.split(".", 1)[1]
        else:
            base_id = model_id

        if base_id in MODEL_IDS.values():
            result[id_to_name[base_id]] = model_id
        else:
            result[base_id] = model_id

    return result
