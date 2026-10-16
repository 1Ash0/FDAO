export default function Loading() {
  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "32px 24px" }}>
      <div style={{ marginBottom: 32 }}>
        <div style={{ height: 18, width: 280, background: "var(--surface-2)", borderRadius: 4, marginBottom: 8 }} className="animate-pulse" />
        <div style={{ height: 13, width: 440, background: "var(--surface-2)", borderRadius: 4 }} className="animate-pulse" />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 1, background: "var(--border)", borderRadius: 8, overflow: "hidden", marginBottom: 32 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ background: "var(--surface)", padding: "14px 16px" }}>
            <div style={{ height: 9, width: 60, background: "var(--surface-2)", borderRadius: 3, marginBottom: 10 }} className="animate-pulse" />
            <div style={{ height: 20, width: 50, background: "var(--surface-2)", borderRadius: 3 }} className="animate-pulse" />
          </div>
        ))}
      </div>
      <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} style={{ padding: "14px 16px", borderBottom: i < 2 ? "1px solid var(--border)" : "none", display: "flex", gap: 16, alignItems: "center" }}>
            <div style={{ height: 13, width: 180, background: "var(--surface-2)", borderRadius: 3 }} className="animate-pulse" />
            <div style={{ height: 13, width: 40, background: "var(--surface-2)", borderRadius: 3 }} className="animate-pulse" />
            <div style={{ height: 3, flex: 1, background: "var(--surface-2)", borderRadius: 3 }} className="animate-pulse" />
          </div>
        ))}
      </div>
    </main>
  )
}
