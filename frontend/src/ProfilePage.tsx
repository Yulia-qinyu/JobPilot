import { FormEvent, useEffect, useRef, useState } from "react";

import { profileApi, workspaceApi } from "./api";
import { ROLE_FAMILIES, ROLE_FAMILY_LABELS, ROLE_PRIORITY_LABELS } from "./decision-utils";
import { canAddTarget, formatUpdatedAt, MAX_TARGETS } from "./profile-utils";
import type {
  Experience,
  ExperienceFact,
  NamedTarget,
  RoleFamily,
  RolePriority,
  TargetRole,
  UserProfile,
  JobSearchStrategy,
  CandidateType,
} from "./types";

const STRATEGIES: { id: JobSearchStrategy; title: string; description: string }[] = [
  { id: "high_volume", title: "高频投递", description: "我想尽可能多投，保持投递节奏。" },
  { id: "focused", title: "重点冲刺", description: "我想集中准备少数重点岗位。" },
  { id: "balanced", title: "平衡模式", description: "我想兼顾投递数量和准备质量。" },
  { id: "interview_first", title: "面试优先", description: "我最近已有面试，优先保证面试推进。" },
];

type ProfileAction = () => Promise<UserProfile>;

const CANDIDATE_TYPES: { id: CandidateType; title: string; description: string }[] = [
  { id: "graduate", title: "应届 / 校招", description: "我以应届毕业生身份参加校园招聘。" },
  { id: "experienced", title: "社招", description: "我主要申请有工作经验的社会招聘岗位。" },
  { id: "both", title: "都可以", description: "我同时考虑符合条件的校招和社招机会。" },
];

export function CandidateIdentityCard({
  candidateType,
  graduationYear,
  busy,
  onSave,
}: {
  candidateType: CandidateType | null;
  graduationYear: number | null;
  busy: boolean;
  onSave: (candidateType: CandidateType | null, graduationYear: number | null) => void;
}) {
  const [selectedType, setSelectedType] = useState<CandidateType | null>(candidateType);
  const [selectedYear, setSelectedYear] = useState<number | null>(graduationYear);
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 9 }, (_, index) => currentYear - 2 + index);
  const supportsCampus = selectedType === "graduate" || selectedType === "both";
  return (
    <section className="profile-card identity-card">
      <div className="profile-card-header"><div><span className="card-kicker">求职身份</span><h2>你以哪种身份申请岗位？</h2><p>这是你主动确认的求职事实，只用于判断明确的校招身份与毕业届别要求。</p></div></div>
      <div className="identity-options">
        {CANDIDATE_TYPES.map((item) => <button type="button" key={item.id} className={selectedType === item.id ? "selected" : ""} aria-pressed={selectedType === item.id} disabled={busy} onClick={() => { setSelectedType(item.id); if (item.id === "experienced") setSelectedYear(null); }}><strong>{item.title}</strong><span>{item.description}</span></button>)}
      </div>
      {supportsCampus && <label className="graduation-year-field">毕业届别<select aria-label="毕业届别" value={selectedYear ?? ""} onChange={(event) => setSelectedYear(event.target.value ? Number(event.target.value) : null)}><option value="">请选择</option>{years.map((year) => <option key={year} value={year}>{year}届</option>)}</select><small>毕业届别与学历是两条独立证据；选择届别不会自动证明学历。</small></label>}
      <div className="identity-actions"><button type="button" className="primary-small" disabled={busy || selectedType === null || (supportsCampus && selectedYear === null)} onClick={() => onSave(selectedType, supportsCampus ? selectedYear : null)}>保存求职身份</button></div>
    </section>
  );
}

const ROLE_SUGGESTIONS: { name: string; family: RoleFamily }[] = [
  { name: "AI Product Manager", family: "ai_product" },
  { name: "FinTech Product Manager", family: "fintech_product" },
  { name: "Data Product Manager", family: "data_product" },
  { name: "Strategy Product Manager", family: "strategy_product" },
];

function LoadingBlock() {
  return <div className="profile-loading"><span className="spinner dark" />正在加载求职档案…</div>;
}

function TargetList({
  title,
  description,
  items,
  placeholder,
  suggestions = [],
  onAdd,
  onRemove,
  onEdit,
  busy,
}: {
  title: string;
  description: string;
  items: NamedTarget[];
  placeholder: string;
  suggestions?: string[];
  onAdd: (name: string) => void;
  onRemove: (id: number) => void;
  onEdit?: (id: number, name: string) => void;
  busy: boolean;
}) {
  const [value, setValue] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const available = suggestions.filter(
    (suggestion) => !items.some((item) => item.name.toLowerCase() === suggestion.toLowerCase()),
  );

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!value.trim()) return;
    onAdd(value.trim());
    setValue("");
  }

  return (
    <section className="profile-card target-card">
      <div className="profile-card-header">
        <div><h2>{title}</h2><p>{description}</p></div>
        <span className="count">{items.length} / {MAX_TARGETS}</span>
      </div>
      <div className="tag-list">
        {items.map((item) => editingId === item.id ? (
          <form className="tag editing" key={item.id} onSubmit={(event) => {
            event.preventDefault();
            if (editValue.trim() && onEdit) onEdit(item.id, editValue.trim());
            setEditingId(null);
          }}>
            <input value={editValue} onChange={(event) => setEditValue(event.target.value)} autoFocus />
            <button type="submit" disabled={busy}>保存</button>
          </form>
        ) : (
          <span className="tag" key={item.id}>
            {onEdit ? <button className="tag-name" onClick={() => { setEditingId(item.id); setEditValue(item.name); }}>{item.name}</button> : item.name}
            <button className="tag-remove" aria-label={`移除 ${item.name}`} onClick={() => onRemove(item.id)} disabled={busy}>×</button>
          </span>
        ))}
        {!items.length && <span className="empty-inline">暂未添加。</span>}
      </div>
      <form className="inline-add" onSubmit={submit}>
        <input value={value} onChange={(event) => setValue(event.target.value)} placeholder={placeholder} disabled={!canAddTarget(items.length) || busy} maxLength={120} />
        <button type="submit" disabled={!value.trim() || !canAddTarget(items.length) || busy}>添加</button>
      </form>
      {available.length > 0 && suggestions.length > 0 && (
        <div className="suggestions"><span>常见岗位</span>{available.slice(0, 3).map((role) => <button key={role} disabled={!canAddTarget(items.length) || busy} onClick={() => onAdd(role)}>+ {role}</button>)}</div>
      )}
    </section>
  );
}

function FactRow({
  fact,
  busy,
  onUpdate,
  onDelete,
}: {
  fact: ExperienceFact;
  busy: boolean;
  onUpdate: (id: number, values: { text?: string; confirmed?: boolean }) => void;
  onDelete: (id: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(fact.text);
  return (
    <div className="fact-row">
      <button
        className={`confirm-control ${fact.confirmed ? "confirmed" : ""}`}
        onClick={() => onUpdate(fact.id, { confirmed: !fact.confirmed })}
        aria-label={fact.confirmed ? "取消确认这条事实" : "确认这条事实"}
        disabled={busy}
      >{fact.confirmed ? "✓" : ""}</button>
      <div className="fact-content">
        {editing ? (
          <form onSubmit={(event) => { event.preventDefault(); onUpdate(fact.id, { text }); setEditing(false); }}>
            <textarea value={text} onChange={(event) => setText(event.target.value)} rows={3} autoFocus />
            <div className="fact-actions"><button type="submit" disabled={busy || text.trim().length < 2}>保存</button><button type="button" onClick={() => { setText(fact.text); setEditing(false); }}>取消</button></div>
          </form>
        ) : <p>{fact.text}</p>}
        <div className="fact-meta"><span className={`source ${fact.source_type}`}>{fact.source_type === "resume" ? "来自简历" : "手动添加"}</span>{fact.confirmed && <span>已确认</span>}</div>
      </div>
      {!editing && <div className="row-actions"><button onClick={() => setEditing(true)}>编辑</button><button onClick={() => onDelete(fact.id)} disabled={busy}>删除</button></div>}
    </div>
  );
}

export function TargetRoleCard({
  roles,
  busy,
  onAdd,
  onUpdate,
  onRemove,
}: {
  roles: TargetRole[];
  busy: boolean;
  onAdd: (name: string, priority: RolePriority) => void;
  onUpdate: (id: number, values: Partial<Pick<TargetRole, "name" | "priority" | "role_family_override">>) => void;
  onRemove: (id: number) => void;
}) {
  const [name, setName] = useState("");
  const [priority, setPriority] = useState<RolePriority>("primary");
  const [editingClassificationId, setEditingClassificationId] = useState<number | null>(null);
  const needsAttention = roles.some((role) => role.effective_role_family === "unknown");
  return <section className="profile-card target-card role-target-card">
    <div className="profile-card-header"><div><h2>目标岗位</h2><p>你决定求职优先级，系统自动识别标准岗位方向。</p></div><span className="count">{roles.length} / {MAX_TARGETS}</span></div>
    {needsAttention && <div className="role-reminder">部分目标岗位暂无法确定分类，请确认后获得更准确的岗位筛选。</div>}
    <div className="target-role-list">
      {roles.map((role) => <div className="target-role-row" key={role.id}>
        <div className="target-role-main">
          <input aria-label={`${role.name} 名称`} defaultValue={role.name} disabled={busy} onBlur={(event) => { const value = event.target.value.trim(); if (value && value !== role.name) onUpdate(role.id, { name: value }); }} />
          <select aria-label={`${role.name} 优先级`} value={role.priority} disabled={busy} onChange={(event) => onUpdate(role.id, { priority: event.target.value as RolePriority })}>{Object.entries(ROLE_PRIORITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          <button className="tag-remove" aria-label={`移除 ${role.name}`} onClick={() => onRemove(role.id)} disabled={busy}>×</button>
        </div>
        <div className={`role-classification ${role.effective_role_family === "unknown" ? "unknown" : ""}`}>
          <span>系统识别</span><strong>{ROLE_FAMILY_LABELS[role.effective_role_family]}</strong>
          {role.role_family_override && <small>手动修正</small>}
          <button type="button" onClick={() => setEditingClassificationId((current) => current === role.id ? null : role.id)}>{editingClassificationId === role.id ? "收起" : "修改分类"}</button>
        </div>
        {role.effective_role_family === "unknown" && <p className="role-unknown-message">暂无法确定岗位分类，请确认。</p>}
        {editingClassificationId === role.id && <div className="role-override-editor">
          <select aria-label={`${role.name} 手动分类`} value={role.role_family_override || role.auto_role_family} disabled={busy} onChange={(event) => onUpdate(role.id, { role_family_override: event.target.value as RoleFamily })}>{ROLE_FAMILIES.filter((value) => value !== "unknown").map((value) => <option key={value} value={value}>{ROLE_FAMILY_LABELS[value]}</option>)}</select>
          {role.role_family_override && <button type="button" disabled={busy} onClick={() => onUpdate(role.id, { role_family_override: null })}>清除手动修正</button>}
        </div>}
      </div>)}
      {!roles.length && <span className="empty-inline">暂未添加。</span>}
    </div>
    <form className="target-role-add" onSubmit={(event) => { event.preventDefault(); if (!name.trim()) return; onAdd(name.trim(), priority); setName(""); }}>
      <input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如：AI Product Manager" disabled={busy || !canAddTarget(roles.length)} />
      <select value={priority} onChange={(event) => setPriority(event.target.value as RolePriority)}>{Object.entries(ROLE_PRIORITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <button type="submit" disabled={busy || !name.trim() || !canAddTarget(roles.length)}>添加</button>
    </form>
    <div className="suggestions"><span>常见岗位</span>{ROLE_SUGGESTIONS.filter((item) => !roles.some((role) => role.name.toLowerCase() === item.name.toLowerCase())).slice(0, 3).map((item) => <button key={item.name} type="button" disabled={busy || !canAddTarget(roles.length)} onClick={() => setName(item.name)}>+ {item.name}</button>)}</div>
  </section>;
}

function ExperienceCard({
  experience,
  busy,
  onAddFact,
  onUpdateFact,
  onDeleteFact,
}: {
  experience: Experience;
  busy: boolean;
  onAddFact: (experienceId: number, text: string) => void;
  onUpdateFact: (id: number, values: { text?: string; confirmed?: boolean }) => void;
  onDeleteFact: (id: number) => void;
}) {
  const [newFact, setNewFact] = useState("");
  return (
    <article className="experience-card">
      <header>
        <span className="experience-type">{experience.experience_type === "work" ? "工作经历" : "项目经历"}</span>
        <div><h3>{experience.title}</h3><p>{experience.organization}{experience.date_range ? ` · ${experience.date_range}` : ""}</p></div>
        <span className="fact-count">{experience.facts.length} 条事实</span>
      </header>
      <div className="facts">
        {experience.facts.map((fact) => <FactRow key={fact.id} fact={fact} busy={busy} onUpdate={onUpdateFact} onDelete={onDeleteFact} />)}
        {!experience.facts.length && <p className="empty-facts">暂时没有事实陈述。</p>}
      </div>
      <form className="fact-add" onSubmit={(event) => { event.preventDefault(); if (newFact.trim()) { onAddFact(experience.id, newFact); setNewFact(""); } }}>
        <input value={newFact} onChange={(event) => setNewFact(event.target.value)} placeholder="添加一条你能够证明的经历事实…" maxLength={2000} />
        <button type="submit" disabled={busy || newFact.trim().length < 2}>添加事实</button>
      </form>
    </article>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const resumeInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    profileApi.get().then((data) => { setProfile(data); setLocation(data.preferred_location || ""); }).catch((cause: Error) => setError(cause.message));
  }, []);

  async function run(action: ProfileAction, success?: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await action();
      setProfile(updated);
      setLocation(updated.preferred_location || "");
      if (success) setNotice(success);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "出现问题，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  if (!profile && !error) return <LoadingBlock />;

  return (
    <main className="profile-shell">
      <header className="profile-hero"><span className="eyebrow">你的求职事实基础</span><h1>求职档案</h1><p>沉淀真实、可核验的经历，为之后的求职决策提供依据。</p></header>
      {error && <div className="error profile-message" role="alert">{error}</div>}
      {notice && <div className="notice profile-message">{notice}</div>}
      {!profile ? <button className="primary-small" onClick={() => window.location.reload()}>重新加载</button> : <>
        <section className="profile-card strategy-card">
          <div className="profile-card-header"><div><span className="card-kicker">我的求职策略</span><h2>你现在更想怎样推进？</h2><p>这会成为未来规划建议的基础，你可以随时修改。</p></div></div>
          <div className="strategy-options">{STRATEGIES.map((strategy) => <button key={strategy.id} className={profile.job_search_strategy === strategy.id ? "selected" : ""} disabled={busy} onClick={() => void run(async () => { await workspaceApi.updateStrategy(strategy.id); return profileApi.get(); }, "求职策略已保存。") }><strong>{strategy.title}</strong><span>{strategy.description}</span></button>)}</div>
        </section>
        <CandidateIdentityCard key={`${profile.candidate_type ?? "unknown"}-${profile.graduation_year ?? "unknown"}`} candidateType={profile.candidate_type} graduationYear={profile.graduation_year} busy={busy} onSave={(candidateType, graduationYear) => void run(() => profileApi.updateIdentity(candidateType, graduationYear), "求职身份已保存，既有匹配分析将按新证据重新验证。") } />
        <section className="profile-card resume-card">
          <div className="profile-card-header"><div><span className="card-kicker">主简历</span><h2>你的核心经历来源</h2><p>解析后形成结构化档案与经历事实库。</p></div><button className="primary-small" onClick={() => resumeInput.current?.click()} disabled={busy}>{profile.resume ? "替换简历" : "上传简历"}</button></div>
          <input className="hidden-input" ref={resumeInput} type="file" accept=".pdf,.docx" onChange={(event) => { const file = event.target.files?.[0]; if (file) void run(() => profileApi.uploadResume(file), "主简历和经历事实库已更新。"); event.target.value = ""; }} />
          {profile.resume ? <div className="resume-file"><span className="document-icon">DOC</span><div><strong>{profile.resume.original_filename}</strong><p>更新于 {formatUpdatedAt(profile.resume.updated_at)}</p></div><span className="stored-status">已保存</span></div> : <button className="empty-resume" onClick={() => resumeInput.current?.click()}><strong>添加主简历</strong><span>PDF 或 DOCX · 最大 10 MB</span></button>}
        </section>

        <div className="profile-grid">
          <TargetList title="目标公司" description="聚焦最想争取的秋招机会。" items={profile.target_companies} placeholder="例如：Atlassian" onAdd={(name) => void run(() => profileApi.addCompany(name))} onRemove={(id) => void run(() => profileApi.deleteCompany(id))} onEdit={(id, name) => void run(() => profileApi.updateCompany(id, name))} busy={busy} />
          <TargetRoleCard roles={profile.target_roles} busy={busy} onAdd={(name, priority) => void run(() => profileApi.addRole(name, priority))} onUpdate={(id, values) => void run(() => profileApi.updateRole(id, values))} onRemove={(id) => void run(() => profileApi.deleteRole(id))} />
        </div>

        <section className="profile-card location-card">
          <div><h2>目标城市</h2><p>填写当前最优先考虑的城市或地区。</p></div>
          <form onSubmit={(event) => { event.preventDefault(); void run(() => profileApi.updateLocation(location.trim() || null), "目标城市已保存。"); }}><input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="例如：Sydney, Australia" maxLength={120} /><button type="submit" disabled={busy}>保存</button></form>
        </section>

        <section className="experience-section">
          <div className="experience-heading"><div><span className="eyebrow">真实经历基础</span><h2>经历事实库</h2><p>确认从简历提取的事实，或添加你能够证明的经历陈述。JobPilot 不会自动编造新事实。</p></div><span>共 {profile.experiences.reduce((sum, item) => sum + item.facts.length, 0)} 条事实</span></div>
          {profile.experiences.length ? profile.experiences.map((experience) => <ExperienceCard key={experience.id} experience={experience} busy={busy} onAddFact={(id, text) => void run(() => profileApi.addFact(id, text))} onUpdateFact={(id, values) => void run(() => profileApi.updateFact(id, values))} onDeleteFact={(id) => void run(() => profileApi.deleteFact(id))} />) : <div className="empty-bank"><h3>经历事实库还是空的。</h3><p>上传主简历后，系统会创建可确认的经历事实。</p></div>}
        </section>
      </>}
    </main>
  );
}
