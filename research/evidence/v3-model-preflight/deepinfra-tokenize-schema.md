> ## Documentation Index
> Fetch the complete documentation index at: https://docs.deepinfra.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Tokenize



## OpenAPI

````yaml https://api.deepinfra.com/openapi.json post /v1/tokenize
openapi: 3.1.0
info:
  title: DeepInfra API
  description: >-
    The DeepInfra API provides serverless AI inference, custom model
    deployments, and GPU rentals.
  version: 1.0.0
servers:
  - url: https://api.deepinfra.com
security: []
tags:
  - name: Chat Completions
    description: OpenAI and Anthropic-compatible chat completion endpoints for LLMs.
  - name: Text Completions
    description: OpenAI-compatible text completion endpoints.
  - name: Embeddings
    description: Generate text embeddings for search and RAG.
  - name: Image Generation
    description: Generate, edit, and create variations of images.
  - name: Audio
    description: OpenAI-compatible speech synthesis, transcription, and translation.
  - name: Text to Speech
    description: ElevenLabs-compatible TTS endpoints and voice management.
  - name: Inference
    description: Native DeepInfra inference API for models and deployments.
  - name: Dedicated Models
    description: Deploy and manage private model instances with autoscaling.
  - name: GPU Rentals
    description: Rent dedicated GPU containers.
  - name: Models
    description: Browse, search, and manage AI models.
  - name: Files & Batches
    description: File uploads and batch processing.
  - name: LoRA Adapters
    description: Create, manage, and query LoRA adapter models.
  - name: Agents
    description: Manage agent-framework instances (OpenClaw and friends).
  - name: Sandboxes
    description: Create and manage isolated sandbox environments.
  - name: Account
    description: User profile, team management, rate limits, and GPU pool limits.
  - name: Authentication
    description: API tokens, SSH keys, scoped JWTs, and login flows.
  - name: Billing
    description: Payment methods, usage tracking, and billing.
  - name: Logs & Metrics
    description: Query inference logs, deployment logs, and usage metrics.
  - name: Utilities
    description: Feedback submission and CLI version.
paths:
  /v1/tokenize:
    post:
      tags:
        - Tokenizer
      summary: Tokenize
      operationId: tokenize_v1_tokenize_post
      parameters:
        - name: xi-api-key
          in: header
          required: false
          schema:
            anyOf:
              - type: string
              - type: 'null'
            title: Xi-Api-Key
        - name: x-api-key
          in: header
          required: false
          schema:
            anyOf:
              - type: string
              - type: 'null'
            title: X-Api-Key
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TokenizeIn'
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenizeOut'
        '422':
          description: Validation Error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HTTPValidationError'
      security:
        - HTTPBearer: []
components:
  schemas:
    TokenizeIn:
      properties:
        model:
          type: string
          title: Model
          description: model name
          examples:
            - my-org/my-dedicated-llm
        prompt:
          anyOf:
            - type: string
            - type: 'null'
          title: Prompt
          description: text to tokenize (completion form)
        messages:
          anyOf:
            - items:
                additionalProperties: true
                type: object
              type: array
            - type: 'null'
          title: Messages
          description: chat messages to tokenize (chat form)
        return_token_strs:
          anyOf:
            - type: boolean
            - type: 'null'
          title: Return Token Strs
          description: also return the per-token strings (vLLM)
      additionalProperties: true
      type: object
      required:
        - model
      title: TokenizeIn
    TokenizeOut:
      properties:
        count:
          type: integer
          title: Count
          description: number of tokens
        max_model_len:
          type: integer
          title: Max Model Len
          description: the model's maximum context length
        tokens:
          items:
            type: integer
          type: array
          title: Tokens
          description: token ids
        token_strs:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Token Strs
          description: per-token strings, if requested (vLLM)
      type: object
      required:
        - count
        - max_model_len
        - tokens
      title: TokenizeOut
    HTTPValidationError:
      properties:
        detail:
          items:
            $ref: '#/components/schemas/ValidationError'
          type: array
          title: Detail
      type: object
      title: HTTPValidationError
    ValidationError:
      properties:
        loc:
          items:
            anyOf:
              - type: string
              - type: integer
          type: array
          title: Location
        msg:
          type: string
          title: Message
        type:
          type: string
          title: Error Type
      type: object
      required:
        - loc
        - msg
        - type
      title: ValidationError
  securitySchemes:
    HTTPBearer:
      type: http
      scheme: bearer

````

This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.