# Phase 7A + 7B Human Product Evaluation

## Discover Experience

- Landing: `今天你想搜索什么机会？` with a ByteDance search URL input.
- Personalization: visibly OFF; Candidate Profile is not read.
- Progress: Ready → Searching → Completed/Partial/Failed with counts and expiry.
- Results: temporary cards with deterministic filters, Why this job, and explicit Add to My Jobs.
- My Jobs: existing persistent Decision Center; no temporary result appears there before Add.

## Live Persistence Test

```json
{
  "search_url": "https://jobs.bytedance.com/experienced/position?keywords=AI+Product+Manager&location=CT_11",
  "state": "Completed",
  "pages_requested": 3,
  "jobs_discovered": 249,
  "temporary_results": 249,
  "search_duration_seconds": 6.128,
  "persistent_jobs_before": 0,
  "persistent_jobs_after_search": 0,
  "search_persistent_delta": 0,
  "add_outcome": "created",
  "add_duration_seconds": 0.035,
  "persistent_jobs_after_add": 1,
  "add_persistent_delta": 1,
  "repeat_add_outcome": "existing",
  "persistent_jobs_after_repeat": 1,
  "phase3_rows": 0,
  "phase3_calls": 0,
  "claude_calls": 0
}
```

## Temporary Result Sample

| External ID | Title | Company | Location | Role Family | Relevance | Why This Job | Already in My Jobs | Relevant | Explanation | Would Add |
|---|---|---|---|---|---|---|---|---|---|---|
| 7295934830696368434 | AI产品工程师-标注Agent产品 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7617832509772302597 | AI产品经理（短剧内容/创作者服务） - 番茄小说 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；检测到明确资格或强制要求 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7613785511052069173 | AI产品工程师-大模型评测 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7623813664374901045 | 世界模型产品经理（应用产品方向） - AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7147905627624147207 | AI产品经理-抖音研发 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7667839080811055365 | 世界模型产品经理（Agent/工程方向） - AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7623729945864440117 | 高级产品经理（大模型数据管理平台）-AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7633273636128393477 | 资深产品经理（机器人/具身智能训练方向）-AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；检测到明确资格或强制要求 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7639347683555133701 | 高级AI产品经理-集团信息系统 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7623793065435728133 | 世界模型产品经理（模型训练方向） - AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；检测到明确资格或强制要求 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7532121022121560328 | AI应用平台高级产品经理-AI Platform | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7411457281215023410 | LLM训练产品经理-AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7650068703044159797 | AI产品经理-抖音生活服务 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7665927440462235909 | AI产品经理（模型方向）-抖音生活服务 | 字节跳动 | 北京、上海 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7628618777886755125 | AI产品工程师（多模态）-AI数据与安全 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7449313662403971336 | AI产品经理-豆包爱学 | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7541314121405958408 | AI产品经理（达人成长方向）-抖音电商（北京） | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7605531121644652805 | AI应用产品经理-抖音生活服务 | 字节跳动 | 上海、北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；检测到明确资格或强制要求 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7630841008290253061 | 高级产品经理（AI创作方向） - 抖音效果与创作 | 字节跳动 | 深圳、北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |
| 7495726975303371015 | AIGC产品经理（即创）-中国广告产品（北京/上海） | 字节跳动 | 北京 | ai_product | High | 符合本次搜索条件：字节跳动；符合本次搜索条件：岗位方向符合当前搜索；符合本次搜索条件：北京；待确认：年限或其他硬性门槛未明确 | No | Yes / Maybe / No | Good / Weak / Wrong | Yes / No |

## UX Review

- Discover clarity:
- My Jobs distinction:
- Why-this-job usefulness:
- Filter usefulness:
- Add-to-My-Jobs clarity:

> Human labels are intentionally blank. No Claude evaluation was used.
