# Phase 7C Human Product Evaluation

## A. Query Understanding

| Raw Query | Parsed Constraints | Method | Clarification | Tags Offered | Intent Correct | Clarification Useful | Tags Useful |
|---|---|---|---|---|---|---|---|
| 北京 AI 产品经理 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": ["北京"], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 北京 AI Agent 产品经理 大厂 | `{"role_terms": ["agent 产品"], "role_families": ["ai_product"], "locations": ["北京"], "companies": [], "company_groups": ["large_tech"], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 上海 FinTech 产品经理 | `{"role_terms": ["fintech 产品"], "role_families": ["fintech_product"], "locations": ["上海"], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | No | — | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 北京应届 AI 产品，不要运营 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": ["北京"], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": ["graduate"]}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| AI 产品，出海和电商都可以 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 不看高级和资深岗的 AI 产品经理 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": ["高级", "资深"], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 腾讯北京产品 | `{"role_terms": [], "role_families": [], "locations": ["北京"], "companies": ["腾讯"], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 帮我找 AI 工作 | `{"role_terms": [], "role_families": [], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 排除运营, 排除解决方案, 排除工程, 排除算法 | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 我想看看大模型平台方向 | `{"role_terms": [], "role_families": [], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| AI 平台产品经理 | `{"role_terms": ["平台产品"], "role_families": ["platform_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 数据产品经理 上海 | `{"role_terms": ["数据产品"], "role_families": ["data_product"], "locations": ["上海"], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 策略产品经理 北京 | `{"role_terms": ["策略产品"], "role_families": ["strategy_product"], "locations": ["北京"], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 增长产品经理 电商 | `{"role_terms": ["增长产品"], "role_families": ["growth_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | No | — | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| AI 评测产品经理 | `{"role_terms": ["产品经理"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 多模态 AI 产品 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| AIGC 内容产品经理 | `{"role_terms": ["产品经理"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | No | — | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| ToB AI 产品经理 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| AI 产品经理，不要解决方案 | `{"role_terms": ["ai 产品"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": []}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 校招 Agent 产品 | `{"role_terms": ["agent 产品"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": ["graduate"]}` | Deterministic | Yes | 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |
| 社招 AI Product Manager | `{"role_terms": ["ai product"], "role_families": ["ai_product"], "locations": [], "companies": [], "company_groups": [], "industries": [], "seniority": [], "recruitment_types": ["experienced"]}` | Deterministic | Yes | AI Agent, 大模型应用, AI 平台, AI 数据, 模型评测, 多模态, AIGC, 电商, 出海 / 国际化, 广告 / 商业化, 金融科技, 内容 / 创作者, 搜索 / 推荐, ToB / 企业服务, Developer Tools | Yes / Partial / No | Yes / No / Unnecessary | Yes / Partial / No |

## B. Discovery Results

| Source | Company | Title | Location | Role Family | Relevance | Matched Reasons | Hard Signals | Excluded | Relevant | Ranking | Explanation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bytedance | 字节跳动 | 商业化产品经理（Ad Agent）-国际化 | 北京 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | Coding Agent产品经理-扣子 | 深圳 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 1+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | Coding Agent产品经理-扣子 | 北京 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 1+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | 企业级Agent应用产品经理-数据平台 | 上海 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | AI产品经理（通用Agent方向）-Aime | 北京 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 1+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | AIGC产品经理（创意Agent方向电商营销）-抖音电商 | 北京 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 3+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | AI产品经理（通用Agent方向）-Aime | 上海 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 1+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | 安全产品经理（Agent安全方向）-AI创新业务 | 北京 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | AIGC产品经理（创意Agent方向/电商营销） - 抖音电商 | 上海、北京 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 3+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | AI Agent产品经理（AgentOS与数据方向） - AI创新业务 | 北京 | ai_product | High | AI Product · Agent · AI Agent | 存在明确学历要求 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | Agent产品经理-火山引擎 | 杭州 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | Agent产品经理-火山引擎 | 北京 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | Agent产品经理-火山引擎 | 深圳 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | AI Agent产品经理 - 剪映CapCut | 深圳、北京 | ai_product | High | AI Product · Agent · AI Agent | 明确要求 1+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| bytedance | 字节跳动 | Agent产品经理-火山引擎 | 上海 | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | AI Product Manager (Coding/Multimodal) | San Francisco, CA | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | Senior AI Product Manager, Code | New York, NY; San Francisco, CA | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | Senior AI Product Manager, Cybersecurity | New York, NY; San Francisco, CA | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | Senior AI Product Manager, Finance Agents | San Francisco, CA; New York, NY | ai_product | High | AI Product · Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:greenhouse | Greenhouse | Engineering Manager, Cloud Platform | British Columbia | unknown | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | AI Applications Ops Manager, GPS | Doha, Qatar  | unknown | Medium | Agent · AI Agent | 明确要求：As a Production AI Ops Manager, you will design and develop the production lifec · 明确要求 6+ 年经验 · 明确要求：For those applying based in Qatar: Residency and employment in Qatar requires ce | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:greenhouse | Greenhouse | Engineering Manager, Cloud Platform | Ontario | unknown | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | AI Builder Intern | San Francisco, CA | unknown | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | AI Infrastructure Engineer, Sandbox Platform | London, UK | unknown | Medium | Agent · AI Agent | 明确要求 4+ 年经验 | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | AI Infrastructure Engineer, Sandbox Platform | San Francisco, CA; Seattle, WA; New York, NY | unknown | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:greenhouse | Greenhouse | Manager, Security Engineering | British Columbia | unknown | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:greenhouse | Greenhouse | Manager, Security Engineering | Ontario | unknown | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:greenhouse | Greenhouse | Senior Product Manager | Ontario | general_product | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:scaleai | Scale AI | Applied AI Engineer, Global Public Sector | Doha, Qatar; London, UK | unknown | Medium | Agent · AI Agent | 明确要求 7+ 年经验 · 明确要求 2+ 年经验 · 明确要求：For those applying based in Qatar: Residency and employment in Qatar requires ce | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |
| greenhouse:greenhouse | Greenhouse | Senior Product Manager | British Columbia | general_product | Medium | Agent · AI Agent | — | No | Yes / Maybe / No | Good / Acceptable / Wrong | Good / Weak / Wrong |

## C. Multi-source

```json
{
  "selected_sources": [
    "bytedance",
    "greenhouse:scaleai",
    "greenhouse:greenhouse"
  ],
  "source_progress": [
    {
      "source": "bytedance",
      "provider": "bytedance",
      "tenant": null,
      "company": "字节跳动",
      "status": "Completed",
      "discovered_count": 166,
      "duration_seconds": 7.0637854158412665,
      "error_code": null
    },
    {
      "source": "greenhouse:scaleai",
      "provider": "greenhouse",
      "tenant": "scaleai",
      "company": "Scale AI",
      "status": "Completed",
      "discovered_count": 166,
      "duration_seconds": 0.9529032919090241,
      "error_code": null
    },
    {
      "source": "greenhouse:greenhouse",
      "provider": "greenhouse",
      "tenant": "greenhouse",
      "company": "Greenhouse",
      "status": "Completed",
      "discovered_count": 16,
      "duration_seconds": 0.19961145799607038,
      "error_code": null
    }
  ],
  "duplicate_count": 0,
  "session_state": "Partial"
}
```

## D. Persistence

```json
{
  "persistent_before": 0,
  "persistent_after_search": 0,
  "persistent_after_add": 1,
  "persistent_after_repeat": 1,
  "add_outcome": "created",
  "repeat_add_outcome": "existing",
  "claude_calls": 0,
  "phase3_calls": 0
}
```

## Human Summary

- Intent Constraint Accuracy:
- Unnecessary Clarification Rate:
- Clarification Usefulness:
- Tag Usefulness:
- Source Routing Accuracy:
- Discovery Precision@10:
- Discovery Precision@20:
- Exclusion Precision:
- Incorrect Hard Exclusion Count:
- Explanation Quality:

> Human labels are intentionally blank. No Claude evaluation was used.
