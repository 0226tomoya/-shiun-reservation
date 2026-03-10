import { useState } from "react";


const BG = "#FFFEEC";
const INK = "#1a1a1a";
const MUTED = "#999";
const BORDER = "#e0dfcf";
const CARD = "#fffff5";

const generateSlots = () => {
  const slots = [];
  for (let h = 12; h < 19; h++) {
    for (let m = 0; m < 60; m += 20) {
      const endM = m + 20, endH = endM >= 60 ? h + 1 : h;
      const label = `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")} – ${String(endH).padStart(2,"0")}:${String(endM%60).padStart(2,"0")}`;
      slots.push({ id: `${h}-${m}`, label, bookings: [], capacity: 5 });
    }
  }
  return slots;
};

const VIEWS = { TOP: "top", CONFIRM: "confirm", CANCEL: "cancel" };

const inputStyle = {
  width: "100%", padding: "13px 16px", borderRadius: 10, border: `1px solid ${BORDER}`,
  background: CARD, color: INK, fontSize: 14, marginBottom: 20,
  outline: "none", boxSizing: "border-box",
};
const primaryBtn = {
  width: "100%", padding: "15px", borderRadius: 10, border: "none",
  background: INK, color: BG, fontWeight: 800, fontSize: 14, cursor: "pointer", letterSpacing: 1,
};
const ghostBtn = {
  width: "100%", padding: "14px", borderRadius: 10,
  border: `1px solid ${BORDER}`, background: "transparent",
  color: MUTED, fontWeight: 600, fontSize: 13, cursor: "pointer", letterSpacing: 1,
};

const Label = ({ children }) => (
  <div style={{ fontSize: 10, color: MUTED, letterSpacing: 2, marginBottom: 8 }}>{children}</div>
);

function Pips({ total, filled }) {
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: i < filled ? INK : BORDER }} />
      ))}
    </div>
  );
}

function Row({ label, value, highlight }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: `1px solid ${BORDER}` }}>
      <div style={{ fontSize: 10, color: MUTED, letterSpacing: 2 }}>{label}</div>
      <div style={{ fontSize: highlight ? 22 : 14, fontWeight: highlight ? 900 : 500, letterSpacing: highlight ? 4 : 0 }}>{value}</div>
    </div>
  );
}

function AdminPage({ slots, onCancel }) {
  const total = slots.reduce((a, s) => a + s.bookings.filter(b => !b.cancelled).length, 0);
  const cancelled = slots.reduce((a, s) => a + s.bookings.filter(b => b.cancelled).length, 0);
  const remaining = slots.reduce((a, s) => a + (s.capacity - s.bookings.filter(b => !b.cancelled).length), 0);

  return (
    <div style={{ fontFamily: "'Helvetica Neue', Arial, sans-serif", maxWidth: 480, margin: "0 auto", minHeight: "100vh", background: "#f5f5f0", color: INK }}>
      <div style={{ background: INK, padding: "32px 24px 24px" }}>
        <div style={{ fontSize: 10, letterSpacing: 4, color: "#777", marginBottom: 6 }}>ADMIN</div>
        <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 0.5, color: "#fff" }}>管理者ダッシュボード</div>
        <div style={{ display: "flex", gap: 24, marginTop: 20 }}>
          {[["予約総数", total], ["キャンセル", cancelled], ["残枠", remaining]].map(([l, v]) => (
            <div key={l}>
              <div style={{ fontSize: 22, fontWeight: 900, color: "#fff" }}>{v}</div>
              <div style={{ fontSize: 10, color: "#666", letterSpacing: 1, marginTop: 2 }}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ padding: "24px 24px 48px" }}>
        <div style={{ fontSize: 10, color: MUTED, letterSpacing: 2, marginBottom: 16 }}>ALL SLOTS</div>
        {slots.map(s => {
          const active = s.bookings.filter(b => !b.cancelled);
          const cxl = s.bookings.filter(b => b.cancelled);
          const full = active.length >= s.capacity;
          return (
            <div key={s.id} style={{ border: `1px solid ${BORDER}`, borderRadius: 12, padding: 16, marginBottom: 12, background: CARD }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: s.bookings.length > 0 ? 12 : 0 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700 }}>{s.label}</div>
                  <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>{active.length}/{s.capacity} 名</div>
                </div>
                <div style={{
                  fontSize: 10, padding: "4px 10px", borderRadius: 20, letterSpacing: 1,
                  background: full ? "#eee" : "#e8f5ee",
                  color: full ? "#999" : "#2e7d52",
                  border: `1px solid ${full ? "#ddd" : "#a8d5b8"}`,
                }}>{full ? "FULL" : "OPEN"}</div>
              </div>
              {active.map(b => (
                <div key={b.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderTop: `1px solid ${BORDER}` }}>
                  <div>
                    <div style={{ fontSize: 13 }}>{b.name}</div>
                    <div style={{ fontSize: 10, color: MUTED, letterSpacing: 1 }}>{b.id}</div>
                  </div>
                  <button onClick={() => onCancel(s.id, b.id)} style={{
                    padding: "4px 12px", borderRadius: 6, border: `1px solid ${BORDER}`,
                    background: "transparent", color: MUTED, fontSize: 11, cursor: "pointer",
                  }}>CANCEL</button>
                </div>
              ))}
              {cxl.map(b => (
                <div key={b.id} style={{ display: "flex", padding: "8px 0", borderTop: `1px solid ${BORDER}`, opacity: 0.4 }}>
                  <div style={{ fontSize: 12, textDecoration: "line-through", color: MUTED }}>{b.name}　</div>
                  <div style={{ fontSize: 10, color: MUTED, letterSpacing: 1, marginTop: 1 }}>CANCELLED</div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CustomerPage({ slots, setSlots }) {
  const [form, setForm] = useState({ name: "", slotId: "" });
  const [myBooking, setMyBooking] = useState(null);
  const [view, setView] = useState(VIEWS.TOP);
  const [error, setError] = useState("");
  const [cancelMsg, setCancelMsg] = useState({ text: "", ok: false });

  const book = () => {
    setError("");
    if (!form.name.trim()) { setError("お名前を入力してください"); return; }
    if (!form.slotId) { setError("時間帯を選択してください"); return; }
    const slot = slots.find(s => s.id === form.slotId);
    if (slot.bookings.filter(b => !b.cancelled).length >= slot.capacity) { setError("この時間帯は満席です"); return; }
    const code = String(Math.floor(100000 + Math.random() * 900000));
    const booking = { id: code, name: form.name.trim(), cancelled: false };
    setSlots(prev => prev.map(s => s.id === form.slotId ? { ...s, bookings: [...s.bookings, booking] } : s));
    setMyBooking({ code, name: form.name.trim(), slotLabel: slot.label, slotId: form.slotId });
    setView(VIEWS.CONFIRM);
    setForm({ name: "", slotId: "" });
  };

  const doCancel = () => {
    setSlots(prev => prev.map(s => ({
      ...s, bookings: s.bookings.map(b => b.id === myBooking.code ? { ...b, cancelled: true } : b)
    })));
    setMyBooking(null);
    setCancelMsg({ text: "予約をキャンセルしました。またのご参加をお待ちしています。", ok: true });
  };

  return (
    <div style={{ fontFamily: "'Helvetica Neue', Arial, sans-serif", maxWidth: 480, margin: "0 auto", minHeight: "100vh", background: BG, color: INK }}>
      <div style={{ padding: "36px 24px 0" }}>
        <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: 0.5 }}>shiun試着会</div>
        <div style={{ fontSize: 13, color: MUTED, marginTop: 6 }}>5/2-3 &nbsp; 12:00 – 19:00</div>
      </div>

      <div style={{ padding: "28px 24px 48px" }}>
        {view === VIEWS.TOP && (
          myBooking ? (
            <div style={{ textAlign: "center", paddingTop: 12 }}>
              <div style={{ fontSize: 10, color: MUTED, letterSpacing: 3, marginBottom: 20 }}>YOUR BOOKING</div>
              <div style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24, marginBottom: 24, textAlign: "left" }}>
                <Row label="NAME" value={myBooking.name} />
                <Row label="TIME" value={myBooking.slotLabel} />
                <Row label="CODE" value={myBooking.code} highlight />
              </div>
              <div style={{ fontSize: 12, color: MUTED, marginBottom: 24, lineHeight: 1.9 }}>
                ご予約は1名につき1回のみです。<br />キャンセルをご希望の場合は下記よりお手続きください。
              </div>
              <button onClick={() => { setView(VIEWS.CANCEL); setCancelMsg({ text: "", ok: false }); }} style={ghostBtn}>
                予約をキャンセルする
              </button>
            </div>
          ) : (
            <>
              <Label>お名前</Label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="山田 太郎" style={inputStyle} />
              <Label>時間帯を選ぶ</Label>
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                {slots.map(s => {
                  const active = s.bookings.filter(b => !b.cancelled).length;
                  const full = active >= s.capacity;
                  const hasCancelled = s.bookings.some(b => b.cancelled);
                  const selected = form.slotId === s.id;
                  return (
                    <button key={s.id} onClick={() => !full && setForm(f => ({ ...f, slotId: s.id }))}
                      disabled={full} style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "14px 18px", borderRadius: 10,
                        border: selected ? `1px solid ${INK}` : `1px solid ${BORDER}`,
                        background: selected ? "#f5f4dc" : CARD,
                        cursor: full ? "not-allowed" : "pointer",
                        opacity: full ? 0.4 : 1, transition: "all 0.15s",
                      }}>
                      <div style={{ textAlign: "left" }}>
                        <div style={{ fontSize: 15, fontWeight: 600 }}>{s.label}</div>
                        {hasCancelled && !full && (
                          <div style={{ fontSize: 10, color: MUTED, marginTop: 3, letterSpacing: 1 }}>CANCELLATION SLOT</div>
                        )}
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <Pips total={s.capacity} filled={active} />
                        <div style={{ fontSize: 11, color: MUTED, marginTop: 4 }}>{active}/{s.capacity}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
              {error && <div style={{ color: "#c0392b", fontSize: 13, marginBottom: 12 }}>{error}</div>}
              <button onClick={book} style={primaryBtn}>予約を確定する</button>
            </>
          )
        )}

        {view === VIEWS.CONFIRM && myBooking && (
          <div style={{ textAlign: "center", paddingTop: 8 }}>
            <div style={{ fontSize: 32, marginBottom: 16 }}>✓</div>
            <div style={{ fontSize: 10, color: MUTED, letterSpacing: 3, marginBottom: 4 }}>BOOKING CONFIRMED</div>
            <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 24 }}>予約が完了しました</div>
            <div style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24, marginBottom: 16, textAlign: "left" }}>
              <Row label="NAME" value={myBooking.name} />
              <Row label="TIME" value={myBooking.slotLabel} />
              <Row label="CODE" value={myBooking.code} highlight />
            </div>
            <div style={{ fontSize: 12, color: MUTED, marginBottom: 28, lineHeight: 1.9 }}>
              予約コードはキャンセル時に必要です。<br />必ずお控えください。<br />なお、ご予約は1名につき1回のみです。
            </div>
            <button onClick={() => { setView(VIEWS.CANCEL); setCancelMsg({ text: "", ok: false }); }} style={ghostBtn}>
              この予約をキャンセルする
            </button>
          </div>
        )}

        {view === VIEWS.CANCEL && (
          <div>
            <button onClick={() => { setView(VIEWS.TOP); setCancelMsg({ text: "", ok: false }); }}
              style={{ background: "none", border: "none", color: MUTED, fontSize: 13, cursor: "pointer", marginBottom: 24, padding: 0, letterSpacing: 1 }}>
              ← BACK
            </button>
            <div style={{ fontSize: 10, color: MUTED, letterSpacing: 3, marginBottom: 20 }}>CANCEL BOOKING</div>
            {cancelMsg.ok ? (
              <div style={{ textAlign: "center", paddingTop: 20 }}>
                <div style={{ fontSize: 28, marginBottom: 12 }}>✓</div>
                <div style={{ fontSize: 14, color: "#2e7d52", lineHeight: 1.9 }}>{cancelMsg.text}</div>
                <button onClick={() => { setView(VIEWS.TOP); setCancelMsg({ text: "", ok: false }); }} style={{ ...ghostBtn, marginTop: 32 }}>
                  トップへ戻る
                </button>
              </div>
            ) : myBooking ? (
              <>
                <div style={{ background: CARD, border: `1px solid ${BORDER}`, borderRadius: 14, padding: 24, marginBottom: 24 }}>
                  <Row label="NAME" value={myBooking.name} />
                  <Row label="TIME" value={myBooking.slotLabel} />
                  <Row label="CODE" value={myBooking.code} highlight />
                </div>
                <div style={{ fontSize: 12, color: MUTED, marginBottom: 20, lineHeight: 1.8 }}>
                  上記の予約をキャンセルします。この操作は取り消せません。
                </div>
                <button onClick={doCancel} style={{ ...primaryBtn, background: INK, color: BG }}>
                  キャンセルを実行する
                </button>
              </>
            ) : (
              <div style={{ textAlign: "center", color: MUTED, fontSize: 14, paddingTop: 20 }}>
                キャンセルできる予約がありません
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [slots, setSlots] = useState(generateSlots());
  const [page, setPage] = useState("customer");

  const adminCancel = (slotId, bookingId) => {
    setSlots(prev => prev.map(s => s.id === slotId
      ? { ...s, bookings: s.bookings.map(b => b.id === bookingId ? { ...b, cancelled: true } : b) }
      : s));
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "center", gap: 0, background: "#e8e8de", borderBottom: "1px solid #d0d0c8" }}>
        {[["customer", "お客様画面"], ["admin", "管理者画面"]].map(([key, label]) => (
          <button key={key} onClick={() => setPage(key)} style={{
            padding: "10px 28px", border: "none", background: "transparent", cursor: "pointer",
            fontSize: 12, fontWeight: 600, letterSpacing: 1,
            color: page === key ? INK : MUTED,
            borderBottom: page === key ? `2px solid ${INK}` : "2px solid transparent",
          }}>{label}</button>
        ))}
      </div>
      {page === "customer" && <CustomerPage slots={slots} setSlots={setSlots} />}
      {page === "admin" && <AdminPage slots={slots} onCancel={adminCancel} />}
    </div>
  );
}