import { useEffect, useState } from 'react'

const params = new URLSearchParams(location.search)
const MAX_ACTIONS = 2
const FAMILY = { marches: 'Marchés', travail: 'Travail', perso: 'Vie perso', entourage: 'Entourage' }

const money = (x, cur) =>
  new Intl.NumberFormat('fr-CA', { style: 'currency', currency: cur, maximumFractionDigits: 0 }).format(x)
const pct = (x) => `${(x * 100).toFixed(1).replace('.', ',')} %`

async function callPlay(seed, country, turns) {
  const r = await fetch('/api/play', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seed, country, turns }),
  })
  const body = await r.json()
  if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Requête invalide.')
  return body
}

function newSeed() {
  return Math.floor(Math.random() * 2 ** 31)
}

export default function App() {
  const [seed, setSeed] = useState(() => Number(params.get('seed')) || newSeed())
  const country = params.get('pays') || null
  const [turns, setTurns] = useState([])
  const [view, setView] = useState(null)
  const [started, setStarted] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    history.replaceState(null, '', `?seed=${seed}${country ? `&pays=${country}` : ''}`)
    setTurns([])
    setStarted(false)
    setError('')
    callPlay(seed, country, []).then(setView, (e) => setError(e.message))
  }, [seed])

  // Joue une ou plusieurs années ; s'arrête dès qu'un choix est attendu.
  async function advance(first, years = 1) {
    setBusy(true)
    setError('')
    let t = turns
    try {
      let v = view
      for (let i = 0; i < years && !v.done && (i === 0 || !v.pending); i++) {
        const next = [...t, i === 0 ? first : { actions: [] }]
        v = await callPlay(seed, country, next)
        t = next
        setView(v)
        setTurns(t)
      }
    } catch (e) {
      setError(e.message)
    }
    setBusy(false)
  }

  if (!view) return <Shell>{error ? <p className="error">{error}</p> : <p>Tirage en cours…</p>}</Shell>
  if (!started) return <Shell><Draw v={view} onStart={() => setStarted(true)} onReroll={() => setSeed(newSeed())} /></Shell>
  if (view.done)
    return (
      <Shell>
        <Mirror v={view} onReplay={() => { setTurns([]); setStarted(false); callPlay(seed, country, []).then(setView) }} onNew={() => setSeed(newSeed())} seed={seed} />
      </Shell>
    )
  return (
    <Shell>
      <Year v={view} busy={busy} error={error} onPlay={advance} />
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="app">
      <header>
        <h1>1 M$, une vie</h1>
      </header>
      <main>{children}</main>
      <footer>
        Jeu de simulation à but pédagogique. Ce n'est pas un conseil financier. Montants en termes réels, sans fiscalité.
      </footer>
    </div>
  )
}

function Draw({ v, onStart, onReroll }) {
  const c = v.country
  const fam = [v.partner ? 'en couple' : 'célibataire', v.children ? `${v.children} enfant${v.children > 1 ? 's' : ''}` : 'sans enfant'].join(', ')
  return (
    <section className="card draw">
      <p className="eyebrow">Votre vie tirée au sort</p>
      <h2>
        Vous avez {v.age} ans et vous vivez au {c.name}.
      </h2>
      <p className="lead">{v.origin}</p>
      <div className="big">
        <span>{money(v.prize_usd, 'USD')}</span>
        <span className="arrow">=</span>
        <span>{money(v.cash, c.currency)}</span>
      </div>
      <p className="muted">
        En pouvoir d'achat local, cela équivaut à <strong>{money(v.cash / c.ppp, 'USD')}</strong> dépensés aux États-Unis.
      </p>
      <dl className="facts">
        <dt>Salaire net</dt><dd>{money(v.salary, c.currency)} / an</dd>
        <dt>Famille</dt><dd>{fam}</dd>
        <dt>Dettes</dt><dd>{v.debt ? money(v.debt, c.currency) : 'aucune'}</dd>
        <dt>Espérance de vie</dt><dd>{c.life_expectancy.toString().replace('.', ',')} ans (mais personne ne connaît la sienne)</dd>
      </dl>
      <div className="row">
        <button className="primary" onClick={onStart}>Vivre cette vie</button>
        <button onClick={onReroll}>Tirer une autre vie</button>
      </div>
    </section>
  )
}

function Year({ v, busy, error, onPlay }) {
  const c = v.country
  const [draft, setDraft] = useState([])
  const [choice, setChoice] = useState(null)
  const full = draft.length >= MAX_ACTIONS
  const add = (a, label) => !full && setDraft([...draft, { ...a, label }])
  const play = (years) => {
    const t = { actions: draft.map(({ label, ...a }) => a), choice }
    setDraft([])
    setChoice(null)
    onPlay(t, years)
  }
  const ly = v.last_year
  const needChoice = v.pending && choice === null

  return (
    <div className="grid">
      <section className="card status">
        <p className="eyebrow">{v.age} ans · {c.name} · {v.working ? 'en activité' : 'à la retraite'}</p>
        <div className="networth">
          <span className="label">Patrimoine net</span>
          <strong>{money(v.net_worth, c.currency)}</strong>
          <span className="muted">≈ {money(v.net_worth_ppp, 'USD')} en pouvoir d'achat</span>
        </div>
        <Spark points={v.history} />
        <dl className="facts">
          <dt>Liquidités</dt><dd>{money(v.cash, c.currency)}</dd>
          <dt className="sub">dont fonds d'urgence</dt><dd className="sub">{money(Math.min(v.emergency_fund, Math.max(v.cash, 0)), c.currency)}</dd>
          <dt>ETF</dt><dd>{money(v.etf, c.currency)}</dd>
          <dt>Immobilier (net)</dt><dd>{money(v.homes.reduce((s, h) => s + h.value - h.mortgage, 0), c.currency)}</dd>
          <dt>Dettes</dt><dd>{money(v.debt, c.currency)}</dd>
          <dt>{v.working ? 'Salaire' : 'Pension'}</dt><dd>{money(ly ? ly.income : v.salary, c.currency)} / an</dd>
          <dt>Dépenses de vie</dt><dd>{money(v.spending, c.currency)} / an</dd>
          <dt>Famille</dt><dd>{v.partner ? 'en couple' : 'seul·e'}{v.children ? ` · ${v.children} enfant(s)` : ''}</dd>
        </dl>
      </section>

      <section className="card">
        {ly ? (
          <>
            <p className="eyebrow">L'an dernier, à {ly.age} ans</p>
            {ly.event && ly.event.id !== v.pending?.id && (
              <div className={`event ${ly.event.family}`}>
                <span className="tag">{FAMILY[ly.event.family]}</span>
                <p>{ly.event.text}</p>
              </div>
            )}
            <p className="muted">
              Bourse : {ly.market_return >= 0 ? '+' : ''}{pct(ly.market_return)} (comme en {ly.market_year}) · inflation {pct(ly.inflation)}
            </p>
            {ly.log.length > 0 && <ul className="log">{ly.log.map((l, i) => <li key={i}>{l}</li>)}</ul>}
          </>
        ) : (
          <p className="eyebrow">Première année : le 1 M$ est sur votre compte.</p>
        )}

        {v.pending && (
          <div className="event pending">
            <span className="tag">{FAMILY[v.pending.family]} · à décider</span>
            <p>{v.pending.text}</p>
            <div className="row">
              {v.pending.choices.map((label, i) => (
                <button key={i} className={choice === i ? 'selected' : ''} onClick={() => setChoice(i)}>{label}</button>
              ))}
            </div>
          </div>
        )}

        <h3>Vos décisions cette année <span className="muted">({draft.length}/{MAX_ACTIONS})</span></h3>
        <p className="muted">Disponible (hors fonds d'urgence) : {money(Math.max(v.available, 0), c.currency)}</p>
        <Actions v={v} add={add} full={full} />
        {draft.length > 0 && (
          <ul className="chips">
            {draft.map((a, i) => (
              <li key={i}>
                {a.label}
                <button aria-label="Retirer" onClick={() => setDraft(draft.filter((_, j) => j !== i))}>×</button>
              </li>
            ))}
          </ul>
        )}
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button className="primary" disabled={busy || needChoice} onClick={() => play(1)}>Année suivante</button>
          <button disabled={busy || needChoice} onClick={() => play(5)}>Avancer de 5 ans</button>
        </div>
      </section>
    </div>
  )
}

function Actions({ v, add, full }) {
  const c = v.country
  const [tab, setTab] = useState('invest')
  const [amount, setAmount] = useState('')
  const [use, setUse] = useState('residence')
  const [size, setSize] = useState(1)
  const [down, setDown] = useState(0.2)
  const avail = Math.max(v.available, 0)
  const price = c.home_price * size

  return (
    <div className="actions">
      <div className="tabs" role="tablist">
        {[['invest', 'Investir (ETF)'], ['home', 'Immobilier'], ['travel', 'Voyager']].map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'selected' : ''} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>
      {tab === 'invest' && (
        <div className="panel">
          <div className="row">
            {[0.25, 0.5, 1].map((f) => (
              <button key={f} onClick={() => setAmount(Math.floor(avail * f))}>{f * 100} %</button>
            ))}
          </div>
          <label>
            Montant ({c.currency}, négatif pour vendre)
            <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
          <button disabled={full || !Number(amount)} onClick={() => {
            const n = Number(amount)
            add({ type: 'invest', amount: n }, `${n > 0 ? 'Investir' : 'Vendre'} ${money(Math.abs(n), c.currency)} en ETF`)
            setAmount('')
          }}>Ajouter</button>
        </div>
      )}
      {tab === 'home' && (
        <div className="panel">
          <label>Usage
            <select value={use} onChange={(e) => setUse(e.target.value)}>
              <option value="residence">Résidence principale (plus de loyer à payer)</option>
              <option value="rental">Locatif (vous touchez des loyers)</option>
            </select>
          </label>
          <label>Taille
            <select value={size} onChange={(e) => setSize(Number(e.target.value))}>
              <option value={0.6}>Petit</option><option value={1}>Moyen</option><option value={1.6}>Grand</option>
            </select>
          </label>
          <label>Mise de fonds
            <select value={down} onChange={(e) => setDown(Number(e.target.value))}>
              <option value={0.2}>20 % (hypothèque 80 %)</option><option value={0.5}>50 %</option><option value={1}>100 % comptant</option>
            </select>
          </label>
          <p className="muted">Prix : {money(price, c.currency)} · à sortir maintenant (mise de fonds + frais) : {money(price * (down + c.buy_costs), c.currency)}</p>
          <button disabled={full} onClick={() => add({ type: 'buy_home', use, size, down }, `Acheter (${use === 'residence' ? 'résidence' : 'locatif'}) ${money(price, c.currency)}`)}>Ajouter</button>
          {v.homes.length > 0 && (
            <ul className="homes">
              {v.homes.map((h, i) => (
                <li key={i}>
                  {h.use === 'residence' ? 'Résidence' : 'Locatif'} · valeur {money(h.value, c.currency)} · hypothèque {money(h.mortgage, c.currency)}
                  <button disabled={full} onClick={() => add({ type: 'sell_home', index: i }, `Vendre le bien n° ${i + 1}`)}>Vendre</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {tab === 'travel' && (
        <div className="panel row">
          <button disabled={full} onClick={() => add({ type: 'travel', kind: 'small' }, `Petit voyage (${money(c.trip_small, c.currency)})`)}>
            Une semaine dans la région · {money(c.trip_small, c.currency)}
          </button>
          <button disabled={full} onClick={() => add({ type: 'travel', kind: 'big' }, `Grand voyage (${money(c.trip_big, c.currency)})`)}>
            Un mois à l'étranger · {money(c.trip_big, c.currency)}
          </button>
        </div>
      )}
    </div>
  )
}

function Spark({ points, height = 70 }) {
  if (points.length < 2) return null
  return <Chart points={points} height={height} axes={false} />
}

function Chart({ points, height = 220, axes = true }) {
  const W = 600, H = height, P = axes ? 40 : 4
  const xs = points.map((p) => p.age), ys = points.map((p) => p.net_worth_ppp)
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const [y0, y1] = [Math.min(0, ...ys), Math.max(...ys, 1)]
  const X = (x) => P + ((x - x0) / Math.max(x1 - x0, 1)) * (W - 2 * P)
  const Y = (y) => H - P / 2 - ((y - y0) / (y1 - y0)) * (H - 1.5 * P)
  const d = points.map((p, i) => `${i ? 'L' : 'M'}${X(p.age).toFixed(1)},${Y(p.net_worth_ppp).toFixed(1)}`).join('')
  const short = (y) => new Intl.NumberFormat('fr-CA', { notation: 'compact', maximumFractionDigits: 1 }).format(y) + ' $'
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Trajectoire du patrimoine net, en pouvoir d'achat">
      {y0 < 0 && <line x1={P} x2={W - P} y1={Y(0)} y2={Y(0)} className="zero" />}
      <path d={d} className="line" />
      {axes && (
        <>
          <text x={P} y={H - 4} className="tick">{x0} ans</text>
          <text x={W - P} y={H - 4} className="tick" textAnchor="end">{x1} ans</text>
          <text x={4} y={Y(y1) + 4} className="tick">{short(y1)}</text>
          <text x={4} y={Y(y0)} className="tick">{short(y0)}</text>
        </>
      )}
    </svg>
  )
}

function Axis({ left, right, value }) {
  return (
    <div className="axis">
      <span>{left}</span>
      <div className="bar"><i style={{ left: `${((value + 1) / 2) * 100}%` }} /></div>
      <span>{right}</span>
    </div>
  )
}

function Mirror({ v, onReplay, onNew, seed }) {
  const m = v.mirror
  const c = v.country
  const [copied, setCopied] = useState(false)
  return (
    <section className="card mirror">
      <p className="eyebrow">Miroir · {c.name}, de {v.start_age} à {v.age} ans</p>
      <h2>Votre vie s'achève à {v.age} ans.</h2>
      <p className="muted">Patrimoine net au fil des années, en pouvoir d'achat (dollars US équivalents).</p>
      <Chart points={m.trajectory} />
      <dl className="stats">
        <div><dt>Patrimoine laissé</dt><dd>{money(m.final_net_worth_ppp, 'USD')}</dd></div>
        <div><dt>Au plus haut</dt><dd>{money(m.peak_net_worth_ppp, 'USD')}</dd></div>
        <div><dt>Années de liberté financière</dt><dd>{m.freedom_years} / {m.years}</dd></div>
        <div><dt>Voyages</dt><dd>{m.trips}</dd></div>
        <div><dt>Argent donné</dt><dd>{money(m.given_ppp, 'USD')}</dd></div>
      </dl>
      <h3>Votre style</h3>
      <p className="muted">Ni bon ni mauvais : une façon de faire parmi d'autres.</p>
      <Axis left="Vivre" right="Bâtir" value={m.vivre_batir} />
      <Axis left="Sécurité" right="Aventure" value={m.securite_aventure} />
      <div className="row">
        <button className="primary" onClick={onNew}>Une autre vie</button>
        <button onClick={onReplay}>Rejouer cette vie</button>
        <button onClick={() => navigator.clipboard?.writeText(location.href).then(() => setCopied(true))}>
          {copied ? 'Lien copié' : 'Partager cette vie'}
        </button>
      </div>
      <p className="muted small">Graine : {seed}. Même graine, même vie de départ et mêmes hasards.</p>
    </section>
  )
}
