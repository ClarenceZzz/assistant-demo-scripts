## request
```
import requests

url = "https://api.siliconflow.cn/v1/chat/completions"

payload = {
    "model": "Qwen/Qwen3-32B",
    "messages": [
        {
            "role": "user",
            "content": "为以下文本块生成一个不超过10个字的简短总结作为高质量、概括性的section元数据，只能返回标题，不能包含其他内容：坐上奥佳华 OG-8598Plus 按摩椅,最直观的感受就是 4D 无刷变频温感机芯带来的按摩流畅感。NIDEC 无刷电机加上四核处理器和 24 颗精密传感器,每一次揉捏、拍打、推拿的力度都精准到毫米级,肩颈处的穴位温度测得从使用前的 30.14°C升到 31.75°C,腰部从 30.15°C升到 32.14°C,腿部从 30.47°C升到 31.37°C,这种明显的温度变化说明血液循环加快、经络得到疏通。对我这种长时间伏案工作的上班族来说,按摩椅就像一个随叫随到的私人理疗师,让肩颈的紧绷感迅速消散,腰酸背痛也能得到缓解。"
        }
    ],
    "stream": False,
    "max_tokens": 4096,
    "enable_thinking": True,
    "thinking_budget": 4096,
    "min_p": 0.05,
    "stop": None,
    "temperature": 0.7,
    "top_p": 0.7,
    "top_k": 50,
    "frequency_penalty": 0.5,
    "n": 1,
    "response_format": { "type": "text" },
    "tools": [
        {
            "type": "function",
            "function": {
                "description": "<string>",
                "name": "<string>",
                "parameters": {},
                "strict": False
            }
        }
    ]
}
headers = {
    "Authorization": "Bearer sk-fvkljvsojrgknsnqftkpnjoxfqvjijitspsvalywcfblvhim",
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)

print(response.json())
```

## response
```
{
  "id": "019a00a78ee27c35ca8e360adc5e3cc6",
  "object": "chat.completion",
  "created": 1760947572,
  "model": "Qwen/Qwen3-32B",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "\n\n4D温感精准按摩",
        "reasoning_content": "\n好的，我现在需要为用户提供的这段关于奥佳华按摩椅的文本生成一个不超过10个字的简短标题。首先，我得通读整个段落，抓住核心内容。用户提到的关键点有4D无刷变频温感机芯、NIDEC无刷电机、四核处理器、24颗传感器、温度变化、血液循环、经络疏通，以及针对上班族的肩颈和腰背问题。\n\n接下来，我需要确定这些信息中的重点。4D无刷变频温感机芯似乎是最主要的卖点，因为它直接影响到按摩的流畅感和效果。温度的变化数据（如肩颈、腰部、腿部的温度上升）显示了产品在促进血液循环和经络疏通方面的效果。另外，用户还强调了这款按摩椅对长时间伏案工作的上班族的缓解作用，相当于私人理疗师。\n\n现在要提炼成10个字以内的标题。首先考虑是否要包含品牌和型号，但用户可能希望更通用一些。关键词可能是“4D无刷温感机芯”或者“精准按摩”，但字数限制严格。需要找到最能概括整体效果的词汇。比如“精准温感按摩”可能不错，但可能超过字数。再想想，“温感按摩精准”可能更紧凑，但不够流畅。或者“4D温感按摩”刚好10个字，涵盖了核心技术和效果。不过用户可能更关注效果，比如“促进血液循环”或者“缓解肩颈腰痛”，但需要结合产品特点。\n\n再分析，原文重点在4D机芯带来的精准控制和温度变化的效果，所以可能需要突出技术带来的结果。比如“4D温感精准按摩”可能超过，但可以简化为“4D温感按摩”或者“精准温感按摩”。但用户要求的是section元数据，可能需要更偏向产品功能而非效果。因此，选择“4D无刷温感按摩”可能更准确，但需要检查字数。“4D无刷温感按摩”是10个字，刚好符合。或者“4D温感精准控制”但可能不够直接。再考虑用户提到的温度变化和经络疏通，或许“温感精准经络通”但可能不够明确。\n\n最终，结合产品核心技术和主要效果，“4D温感精准按摩”是10个字，准确传达了技术特点和按摩效果，符合用户需求。需要确认是否还有更简洁的表达，比如“4D温感按摩”也是10个字，但可能缺少“精准”这一关键点。用户强调了毫米级的力度精准，所以“精准”很重要。因此，最佳选择可能是“4D温感精准按摩”。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 240,
    "completion_tokens": 582,
    "total_tokens": 822,
    "completion_tokens_details": {
      "reasoning_tokens": 575
    }
  },
  "system_fingerprint": ""
}
```