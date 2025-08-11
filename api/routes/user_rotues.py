{
  "nodes": [
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $node['Pick fields'].json.text }}",
              "operation": "regex",
              "value2": "^登陸\\s+.+"
            },
            {
              "value1": "={{ $node['Pick fields'].json.text }}",
              "operation": "equal",
              "value2": "是"
            },
            {
              "value1": "={{ $node['Pick fields'].json.text }}",
              "operation": "equal",
              "value2": "否"
            }
          ]
        },
        "combineOperation": "any"
      },
      "id": "c5b9b7a1-7b6e-4d1b-8d4d-usr-if-1",
      "name": "IF 登陸 / 是 / 否",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [
        800,
        600
      ]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "={{ $env.APP_BASE_URL }}/api/user/register",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"line_user_id\": \"{{$node['Pick fields'].json.userId}}\",\n  \"text\": \"{{$node['Pick fields'].json.text}}\"\n}",
        "options": {}
      },
      "id": "4c0f0a7b-1e3d-4c0a-9d1f-user-reg",
      "name": "USER 註冊 / register",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1040,
        520
      ]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://api.line.me/v2/bot/message/reply",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}"
            },
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"replyToken\": \"{{$node['Pick fields'].json.replyToken}}\",\n  \"messages\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"{{$node['USER 註冊 / register'].json.message}}\"\n    }\n  ]\n}"
      },
      "id": "0f2b9b2e-bc7c-4a1f-9e3c-reply-reg",
      "name": "回覆 Register 結果",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1280,
        520
      ]
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $node['Pick fields'].json.text }}",
              "operation": "regex",
              "value2": "^[\\?？]$"
            }
          ]
        }
      },
      "id": "9d7f3f4a-7f9a-4b52-9e10-qmark-if",
      "name": "IF 問號 ?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [
        1040,
        720
      ]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "={{ $env.APP_BASE_URL }}/api/user/my-cases",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"line_user_id\": \"{{$node['Pick fields'].json.userId}}\"\n}",
        "options": {}
      },
      "id": "f7b5d2a1-7c0e-4a3a-8a2c-user-mycases",
      "name": "USER 我的案件 / my-cases",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1280,
        720
      ]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://api.line.me/v2/bot/message/reply",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}"
            },
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"replyToken\": \"{{$node['Pick fields'].json.replyToken}}\",\n  \"messages\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"{{$node['USER 我的案件 / my-cases'].json.message}}\"\n    }\n  ]\n}"
      },
      "id": "b8a2e0d1-3f7c-4f8f-9c11-reply-mycases",
      "name": "回覆 MyCases 結果",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1520,
        720
      ]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "https://api.line.me/v2/bot/message/reply",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.LINE_CHANNEL_ACCESS_TOKEN }}"
            },
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={\n  \"replyToken\": \"{{$node['Pick fields'].json.replyToken}}\",\n  \"messages\": [\n    {\n      \"type\": \"text\",\n      \"text\": \"請輸入「登陸 您的大名」來綁定，或輸入「?」查詢個人案件。\"\n    }\n  ]\n}"
      },
      "id": "a1f0d3e2-5b4c-4d7e-a3f2-reply-guide",
      "name": "回覆 教學（其它文字）",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1280,
        880
      ]
    }
  ],
  "connections": {
    "IF 登陸 / 是 / 否": {
      "main": [
        [
          {
            "node": "USER 註冊 / register",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "IF 問號 ?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "USER 註冊 / register": {
      "main": [
        [
          {
            "node": "回覆 Register 結果",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "IF 問號 ?": {
      "main": [
        [
          {
            "node": "USER 我的案件 / my-cases",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "回覆 教學（其它文字）",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
