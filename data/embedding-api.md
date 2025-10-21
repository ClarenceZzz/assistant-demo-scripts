##request
```
import requests

url = "https://api.siliconflow.cn/v1/embeddings"

payload = {
    "model": "Qwen/Qwen3-Embedding-8B",
    "input": "Silicon flow embedding online: fast, affordable, and high-quality embedding services. come try it out!",
    "encoding_format": "float",
    "dimensions": 1536
}
headers = {
    "Authorization": "Bearer sk-fvkljvsojrgknsnqftkpnjoxfqvjijitspsvalywcfblvhim",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())
```

##response
```
{
  "object": "list",
  "data": [
    {
      "embedding": [
        0.03703881427645683,
        -0.007845660671591759,
        0.01696852222084999,
        -0.03466687351465225,
        0.01669483631849289,
        -0.014687806367874146,
        -0.039228301495313644,
        -0.03229492902755737,
        0.00012258844799362123,
        ... 
      ],
      "index": 0,
      "object": "embedding"
    }
  ],
  "model": "Qwen/Qwen3-Embedding-8B",
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 0,
    "total_tokens": 22
  }
}
```