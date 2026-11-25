import { useEffect, useState, useRef, useCallback } from 'react'

const params = new URLSearchParams(location.search)
// En production (site statique), l'adresse de l'API vient de VITE_API_URL ; en local, le proxy Vite s'en charge.
const API = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const FAMILY = { marches: 'Marchés', travail: 'Travail', perso: 'Vie perso', entourage: 'Entourage' }

// Durée avant d'afficher le message de réveil (ms) et timeout max (ms)
const WAKE_THRESHOLD = 3000
const MAX_WAIT = 90000

const money = (x, cur) =>
  new Intl.NumberFormat('fr-CA', { style: 'currency', currency: cur, maximumFractionDigits: 0 }).format(x)
const pct = (x) => `${(x * 100).toFixed(1).replace('.', ',')} %`

function newSeed() {
  return Math.floor(Math.random() * 2 ** 31)
}

// Sauvegarde de la partie en cours (graine + décisions) : un rechargement la reprend.
const SAVE_KEY = 'jeu1m.partie'
function loadSave() {
  try {
    return JSON.parse(localStorage.getItem(SAVE_KEY))
  } catch {
    return null
  }
}
function writeSave(game) {
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify(game))
  } catch {
    /* navigation privée ou stockage bloqué : le jeu marche sans sauvegarde */
  }
}

// Mode réaliste : le profil voyage dans l'URL pour qu'un lien redonne la même vie.
const PROFILE_PARAMS = { pays: 'country', age: 'age', salaire: 'salary', dettes: 'debt', montant: 'amount', couple: 'partner', enfants: 'children' }
function profileFromUrl() {
  if (!params.has('montant')) return null
  const p = {}
  for (const [q, k] of Object.entries(PROFILE_PARAMS)) p[k] = params.get(q)
  return { ...p, age: Number(p.age), salary: Number(p.salary), debt: Number(p.debt || 0), amount: Number(p.amount),
    partner: p.partner === '1', children: Number(p.children || 0) }
}
function urlFor(seed, country, profile, level) {
  const q = new URLSearchParams({ seed })
  if (level === 'avance') q.set('niveau', 'avance')
  if (profile) {
    for (const [name, k] of Object.entries(PROFILE_PARAMS)) q.set(name, k === 'partner' ? (profile.partner ? 1 : 0) : profile[k])
  } else if (country) q.set('pays', country)
  return `?${q}`
}

const urlSeed = Number(params.get('seed')) || null
const urlProfile = profileFromUrl()
// Niveau d'affichage : 'decouverte' (jeu de base) ou 'avance' (outils en plus) ; le moteur est le même.
const urlLevel = params.get('niveau') === 'avance' ? 'avance' : 'decouverte'
const saved = loadSave()
// Un lien partagé vers une autre vie l'emporte sur la sauvegarde.
const resume = saved && Number.isInteger(saved.seed) && Array.isArray(saved.turns)
  && (!urlSeed || (saved.seed === urlSeed && JSON.stringify(saved.profile ?? null) === JSON.stringify(urlProfile))) ? saved : null
const initialProfile = resume ? resume.profile ?? null : urlProfile

export default function App() {
  const [seed, setSeed] = useState(() => resume?.seed ?? urlSeed ?? newSeed())
  const [country] = useState(() => (resume ? resume.country : params.get('pays')) || null)
  const [profile, setProfile] = useState(initialProfile)
  // null : écran d'accueil ; 'jeu' : vie tirée au sort ; 'realiste' : le joueur saisit sa situation
  const [mode, setMode] = useState(() => (resume || urlSeed ? (initialProfile ? 'realiste' : 'jeu') : null))
  const [level, setLevel] = useState(() => resume?.level ?? urlLevel)
  const [turns, setTurns] = useState(() => resume?.turns ?? [])
  const [view, setView] = useState(null)
  const [started, setStarted] = useState(() => resume?.started ?? false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [wakeMessage, setWakeMessage] = useState(false)
  const [retryError, setRetryError] = useState(null)
  const ready = mode === 'jeu' || (mode === 'realiste' && profile)

  // Hook pour appeler l'API avec gestion du message de réveil et timeout 90s
  const callPlayWithWake = useCallback(async (seed, country, turns, profile, level) => {
    let wakeTimer = null
    let abortTimer = null
    const controller = new AbortController()

    const showWake = () => setWakeMessage(true)
    const hideWake = () => setWakeMessage(false)

    // Afficher le message après 3 secondes
    wakeTimer = setTimeout(showWake, WAKE_THRESHOLD)
    // Abandonner après 90 secondes
    abortTimer = setTimeout(() => controller.abort(), MAX_WAIT)

    try {
      const r = await fetch(`${API}/api/play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seed, country, turns, profile, level }),
        signal: controller.signal,
      })
      // Seule une réponse 4xx est une vraie erreur de l'API (e.api) ; le reste (5xx, réseau, délai) se réessaie.
      if (r.status >= 400 && r.status < 500) {
        const body = await r.json().catch(() => ({}))
        throw Object.assign(new Error(typeof body.detail === 'string' ? body.detail : 'Requête invalide.'), { api: true })
      }
      if (!r.ok) throw new Error(`Le serveur a répondu ${r.status}.`)
      return await r.json()
    } catch (e) {
      if (e.api) throw e
      throw new Error(e.name === 'AbortError' ? 'Le serveur ne répond pas depuis plus de 90 secondes.' : 'Impossible de joindre le serveur.')
    } finally {
      clearTimeout(wakeTimer)
      clearTimeout(abortTimer)
      hideWake()
    }
  }, [])

  // Rejoue la vie jusqu'aux décisions t ; une panne du serveur propose « Réessayer » sans rien effacer.
  function load(t) {
    setError('')
    setRetryError(null)
    const fail = (e) => (e.api ? setError(e.message) : setRetryError({ message: e.message }))
    callPlayWithWake(seed, country, t, profile, level).then(setView, (e) => {
      if (!e.api || !t.length) return fail(e)
      // sauvegarde illisible (données du jeu modifiées depuis) : on repart du début de cette vie
      setError(`Partie sauvegardée impossible à reprendre (${e.message}). Elle recommence au début.`)
      setTurns([])
      setStarted(false)
      callPlayWithWake(seed, country, [], profile, level).then(setView, fail)
    })
  }

  useEffect(() => {
    if (!ready) return
    history.replaceState(null, '', urlFor(seed, country, profile, level))
    load(turns)
  }, [seed, ready, JSON.stringify(profile)]) // eslint-disable-line react-hooks/exhaustive-deps -- les décisions sont rejouées une fois au chargement

  useEffect(() => {
    if (ready) writeSave({ seed, country, profile, turns, started, level })
  }, [ready, seed, country, profile, turns, started, level])

  function newLife() {
    setTurns([])
    setStarted(false)
    setView(null)
    setSeed(newSeed())
  }

  function home() {
    try {
      localStorage.removeItem(SAVE_KEY)
    } catch {
      /* stockage bloqué : rien à effacer */
    }
    setMode(null)
    setProfile(null)
    setView(null)
    setTurns([])
    setStarted(false)
    setSeed(newSeed()) // sinon « Une vie tirée au sort » redonne la vie abandonnée
    history.replaceState(null, '', location.pathname)
  }

  function submitProfile(p) {
    setProfile(p)
    newLife()
  }

  function replayLife() {
    setTurns([])
    setStarted(false)
    setView(null)
    load([])
  }

  // Joue une ou plusieurs années ; s'arrête dès qu'un choix est attendu.
  async function advance(first, years = 1) {
    setBusy(true)
    setError('')
    setRetryError(null)
    let t = turns
    let i = 0
    try {
      let v = view
      for (; i < years && !v.done && (i === 0 || !v.pending); i++) {
        const next = [...t, i === 0 ? first : { actions: [] }]
        v = await callPlayWithWake(seed, country, next, profile, level)
        t = next
        setView(v)
        setTurns(t)
      }
    } catch (e) {
      // panne du serveur : on garde la décision et les années restantes pour « Réessayer »
      if (e.api) setError(e.message)
      else setRetryError({ message: e.message, first: i === 0 ? first : { actions: [] }, years: years - i })
    }
    setBusy(false)
  }

  if (!mode) return <Shell wakeMessage={wakeMessage}><Landing level={level} onLevel={setLevel} onGame={() => setMode('jeu')} onReal={() => setMode('realiste')} /></Shell>
  if (mode === 'realiste' && !profile) return <Shell onHome={home} wakeMessage={wakeMessage}><ProfileForm onSubmit={submitProfile} /></Shell>
  if (!view) return <Shell onHome={home} wakeMessage={wakeMessage}>{retryError ? (
      <div className="error-retry">
        <p className="error">{retryError.message}</p>
        <button className="primary" onClick={() => load(turns)}>Réessayer</button>
      </div>
    ) : error ? <p className="error">{error}</p> : <p>Tirage en cours…</p>}</Shell>
  if (!started) {
    return (
      <Shell onHome={home} wakeMessage={wakeMessage}>
        <Draw v={view} onStart={() => setStarted(true)}
          onReroll={mode === 'jeu' ? newLife : () => { setProfile(null); setView(null) }} />
      </Shell>
    )
  }
  if (view.done)
    return (
      <Shell onHome={home} wakeMessage={wakeMessage}>
        <Mirror v={view} level={level} onReplay={replayLife} onNew={home} seed={seed} />
      </Shell>
    )
  return (
    <Shell onHome={home} wakeMessage={wakeMessage}>
      <Year v={view} level={level} busy={busy} error={error} retryError={retryError} onRetry={() => advance(retryError.first, retryError.years)} onPlay={advance} onNew={home} />
    </Shell>
  )
}

function Landing({ level, onLevel, onGame, onReal }) {
  return (
    <section className="card draw">
      <p className="eyebrow">Un jeu sur l'argent et le hasard</p>
      <h2>Que feriez-vous d'un million ?</h2>
      <p className="lead">
        Le même million ne vaut pas la même chose selon le pays, l'âge ou le salaire. Vivez une vie année après année, puis regardez ce que vous en avez fait.
      </p>
      <p className="eyebrow step">1. Niveau</p>
      <div className="level" role="radiogroup" aria-label="Niveau">
        {[['decouverte', 'Découverte', 'Le jeu simple : vos décisions et votre patrimoine.'],
          ['avance', 'Avancé', "En plus : 3 décisions par an, une répartition automatique de votre argent et l'économie de votre vie."]].map(([k, l, d]) => (
          <button key={k} role="radio" aria-checked={level === k} className={level === k ? 'selected' : ''} onClick={() => onLevel(k)}>
            <strong>{l}</strong> <span className="muted small">{d}</span>
          </button>
        ))}
      </div>
      <p className="eyebrow step">2. Votre vie</p>
      <div className="choices">
        <button className="choice" onClick={onGame}>
          <strong>Une vie tirée au sort</strong>
          <span>Pays, âge, salaire et famille au hasard. Vous recevez 1 M$ US.</span>
        </button>
        <button className="choice" onClick={onReal}>
          <strong>Ma situation</strong>
          <span>Vous saisissez votre profil et le montant de votre choix.</span>
        </button>
      </div>
    </section>
  )
}

function ProfileForm({ onSubmit }) {
  const [list, setList] = useState(null)
  const [error, setError] = useState('')
  const [f, setF] = useState({ country: 'CA', age: 35, salary: '', debt: 0, amount: '', partner: false, children: 0 })
  useEffect(() => {
    fetch(`${API}/api/countries`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setList, () => setError('Impossible de charger la liste des pays.'))
  }, [])
  const c = list?.find((x) => x.code === f.country)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  function submit(e) {
    e.preventDefault()
    onSubmit({
      country: f.country, age: Number(f.age), partner: f.partner, children: Number(f.children),
      salary: Number(f.salary === '' ? c.salary_median : f.salary),
      debt: Number(f.debt || 0),
      amount: Number(f.amount === '' ? Math.round(c.prize_local) : f.amount),
    })
  }

  if (error) return <p className="error">{error}</p>
  if (!list) return <p>Chargement…</p>
  return (
    <form className="card draw form" onSubmit={submit}>
      <p className="eyebrow">Ma situation</p>
      <h2>Votre profil</h2>
      <p className="muted">Montants annuels bruts, en {c.currency}. Rien n'est envoyé ailleurs que dans le calcul de cette partie.</p>
      <label>Pays
        <select value={f.country} onChange={(e) => setF({ ...f, country: e.target.value, salary: '', amount: '' })}>
          {list.map((x) => <option key={x.code} value={x.code}>{x.name}</option>)}
        </select>
      </label>
      <div className="grid2">
        <label>Âge
          <input type="number" required min={18} max={90} value={f.age} onChange={set('age')} />
        </label>
        <label>Salaire annuel ({c.currency})
          <input type="number" min={0} placeholder={`médian : ${Math.round(c.salary_median)}`} value={f.salary} onChange={set('salary')} />
        </label>
        <label>Dettes hors hypothèque ({c.currency})
          <input type="number" min={0} value={f.debt} onChange={set('debt')} />
        </label>
        <label>Montant reçu ({c.currency})
          <input type="number" min={1} placeholder={`1 M$ US = ${Math.round(c.prize_local)}`} value={f.amount} onChange={set('amount')} />
        </label>
        <label>Enfants à charge
          <input type="number" min={0} max={10} value={f.children} onChange={set('children')} />
        </label>
        <label className="check">
          <input type="checkbox" checked={f.partner} onChange={set('partner')} /> En couple
        </label>
      </div>
      <div className="row">
        <button className="primary" type="submit">Continuer</button>
      </div>
    </form>
  )
}

function Shell({ children, onHome, wakeMessage }) {
  return (
    <div className="app">
      <header>
        <h1>{onHome ? <button className="link title" onClick={onHome}>Et si… ?</button> : 'Et si… ?'}</h1>
      </header>
      {wakeMessage && (
        <div className="wake-banner" role="status" aria-live="polite">
          Le serveur se réveille, ça peut prendre jusqu'à une minute…
        </div>
      )}
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
  const real = v.mode === 'realiste'
  return (
    <section className="card draw">
      <p className="eyebrow">{real ? 'Votre situation' : 'Votre vie tirée au sort'}</p>
      <h2>
        Vous avez {v.age} ans et vous vivez {c.where}.
      </h2>
      <p className="lead">{v.origin}</p>
      <div className="big">
        {!real && <><span>{money(v.prize_usd, 'USD')}</span><span className="arrow">=</span></>}
        <span>{money(v.prize_local, c.currency)}</span>
      </div>
      <p className="muted">
        En pouvoir d'achat local, cela équivaut à <strong>{money(v.prize_local / c.ppp, 'USD')}</strong> dépensés aux États-Unis.
      </p>
      <dl className="facts">
        <dt>Salaire</dt><dd>{money(v.salary, c.currency)} / an</dd>
        <dt>Famille</dt><dd>{fam}</dd>
        <dt>Dettes</dt><dd>{v.debt ? money(v.debt, c.currency) : 'aucune'}</dd>
        <dt>Espérance de vie</dt><dd>{c.life_expectancy.toString().replace('.', ',')} ans (mais personne ne connaît la sienne)</dd>
      </dl>
      <div className="row">
        <button className="primary" onClick={onStart}>Vivre cette vie</button>
        <button onClick={onReroll}>{real ? 'Modifier ma situation' : 'Tirer une autre vie'}</button>
      </div>
    </section>
  )
}

function situation(v) {
  if (v.studying) return 'en études à l\'étranger'
  if (v.business) return 'à son compte'
  return v.retired ? 'à la retraite' : 'en activité'
}

function incomeLabel(v) {
  if (v.studying) return 'Revenu (études)'
  if (v.business) return 'Bénéfice de l\'entreprise'
  return v.retired ? 'Pension' : 'Salaire'
}

function Year({ v, level, busy, error, retryError, onRetry, onPlay, onNew }) {
  const c = v.country
  const [draft, setDraft] = useState([])
  const [choice, setChoice] = useState(null)
  const full = draft.length >= v.max_actions
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
      <div className="col">
      <section className="card status">
        <p className="eyebrow">{v.age} ans · {c.name} · {situation(v)}</p>
        <div className="networth">
          <span className="label">Patrimoine net</span>
          <strong>{money(v.net_worth, c.currency)}</strong>
          <span className="muted">≈ {money(v.net_worth_ppp, 'USD')} en pouvoir d'achat</span>
        </div>
        <dl className="facts">
          <dt>Liquidités</dt><dd>{money(v.cash, c.currency)}</dd>
          <dt className="sub">dont fonds d'urgence</dt><dd className="sub">{money(Math.min(v.emergency_fund, Math.max(v.cash, 0)), c.currency)}</dd>
          <dt>ETF</dt><dd>{money(v.etf, c.currency)}</dd>
          <dt>Immobilier (net)</dt><dd>{money(v.homes.reduce((s, h) => s + h.value - h.mortgage, 0), c.currency)}</dd>
          {v.business && <><dt>Entreprise</dt><dd>{money(v.business.value, c.currency)}</dd></>}
          <dt>Dettes</dt><dd>{money(v.debt, c.currency)}</dd>
          <dt>{incomeLabel(v)}</dt><dd>{money(ly ? ly.income : v.salary, c.currency)} / an</dd>
          <dt>Dépenses de vie</dt><dd>{money(v.spending, c.currency)} / an</dd>
          <dt>Famille</dt><dd>{v.partner ? 'en couple' : 'seul·e'}{v.children ? ` · ${v.children} enfant(s)` : ''}</dd>
        </dl>
      </section>
      <section className="card chart-card">
        <h3>Votre patrimoine au fil des années <span className="muted small">(en pouvoir d'achat)</span></h3>
        <Chart points={v.history} start={v.prize_local / c.ppp} height={230} W={420} />
        {level === 'avance' && <Economy points={v.history} W={420} />}
      </section>
      </div>

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

        <h3>Vos décisions cette année <span className="muted">({draft.length}/{v.max_actions})</span></h3>
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
        {retryError && (
          <div className="error-retry">
            <p className="error">{retryError.message}</p>
            <button className="primary" disabled={busy} onClick={onRetry}>Réessayer</button>
          </div>
        )}
        {error && !retryError && <p className="error">{error}</p>}
        <div className="row">
          <button className="primary" disabled={busy || needChoice} onClick={() => play(1)}>Année suivante</button>
          <button disabled={busy || needChoice} onClick={() => play(5)}>Avancer de 5 ans</button>
        </div>
        <p className="muted small">
          Partie sauvegardée dans ce navigateur.{' '}
          <button className="link" onClick={onNew}>Abandonner et tirer une autre vie</button>
        </p>
      </section>
    </div>
  )
}

// Saisie d'un montant avec raccourcis (en part de `base`) et un bouton « Ajouter ».
function AmountPicker({ label, base, shortcuts = [0.25, 0.5, 1], full, allowNegative = false, onAdd, min = 0 }) {
  const [amount, setAmount] = useState('')
  const n = Number(amount)
  const ok = Number.isFinite(n) && n !== 0 && (allowNegative || n > 0) && Math.abs(n) >= min
  return (
    <>
      <div className="row">
        {shortcuts.map((f) => (
          <button key={f} onClick={() => setAmount(Math.floor(base * f))}>{Math.round(f * 100)} %</button>
        ))}
      </div>
      <label>
        {label}
        <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </label>
      <button disabled={full || !ok} onClick={() => { onAdd(n); setAmount('') }}>Ajouter</button>
    </>
  )
}

const TABS = [
  ['invest', 'Investir (ETF)'], ['home', 'Immobilier'], ['travel', 'Voyager'], ['debt', 'Dettes'],
  ['study', 'Étudier'], ['business', 'Entreprendre'], ['give', 'Donner'], ['rebalance', 'Répartition'],
]

function Actions({ v, add, full }) {
  const c = v.country
  const p = v.prices
  const cur = c.currency
  const [tab, setTab] = useState('invest')
  const [use, setUse] = useState('residence')
  const [size, setSize] = useState(1)
  const [down, setDown] = useState(0.2)
  const avail = Math.max(v.available, 0)
  const price = c.home_price * size
  const canStudy = !v.studied && !v.business && !v.retired && v.age <= p.study_max_age

  return (
    <div className="actions">
      <div className="tabs" role="tablist">
        {TABS.filter(([k]) => k !== 'rebalance' || v.level === 'avance').map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'selected' : ''} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>
      {tab === 'invest' && (
        <div className="panel">
          <p className="muted">Un ETF d'actions de votre pays, dividendes réinvestis. Vous détenez {money(v.etf, cur)}.</p>
          <AmountPicker label={`Montant (${cur}, négatif pour vendre)`} base={avail} full={full} allowNegative
            onAdd={(n) => add({ type: 'invest', amount: n }, `${n > 0 ? 'Investir' : 'Vendre'} ${money(Math.abs(n), cur)} en ETF`)} />
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
          <p className="muted">Prix : {money(price, cur)} · à sortir maintenant (mise de fonds + frais) : {money(price * (down + c.buy_costs), cur)}</p>
          <button disabled={full} onClick={() => add({ type: 'buy_home', use, size, down }, `Acheter (${use === 'residence' ? 'résidence' : 'locatif'}) ${money(price, cur)}`)}>Ajouter</button>
          {v.homes.length > 0 && (
            <ul className="homes">
              {v.homes.map((h, i) => (
                <li key={i}>
                  {h.use === 'residence' ? 'Résidence' : 'Locatif'} · valeur {money(h.value, cur)} · hypothèque {money(h.mortgage, cur)}
                  <button disabled={full} onClick={() => add({ type: 'sell_home', index: i }, `Vendre le bien n° ${i + 1}`)}>Vendre</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {tab === 'travel' && (
        <div className="panel row">
          <button disabled={full} onClick={() => add({ type: 'travel', kind: 'small' }, `Petit voyage (${money(p.trip_small, cur)})`)}>
            Quelques jours pas trop loin · {money(p.trip_small, cur)}
          </button>
          <button disabled={full} onClick={() => add({ type: 'travel', kind: 'big' }, `Grand voyage (${money(p.trip_big, cur)})`)}>
            Deux semaines outre-mer · {money(p.trip_big, cur)}
          </button>
        </div>
      )}
      {tab === 'debt' && (
        <div className="panel">
          {v.debt <= 0 && !v.homes.some((h) => h.mortgage > 0) && <p className="muted">Vous n'avez aucune dette.</p>}
          {v.debt > 0 && (
            <>
              <p className="muted">Dette de consommation : {money(v.debt, cur)}. La rembourser fait disparaître ses mensualités.</p>
              <div className="row">
                <button disabled={full || v.debt > avail} onClick={() => add({ type: 'repay', target: 'debt', amount: v.debt }, `Rembourser toute la dette (${money(v.debt, cur)})`)}>
                  Tout rembourser · {money(v.debt, cur)}
                </button>
              </div>
            </>
          )}
          {v.homes.map((h, i) => h.mortgage > 0 && (
            <div key={i} className="row">
              <span className="muted">Hypothèque du bien n° {i + 1} : {money(h.mortgage, cur)}</span>
              <button disabled={full} onClick={() => {
                const amt = Math.floor(Math.min(h.mortgage, avail))
                if (amt > 0) add({ type: 'repay', target: i, amount: amt }, `Rembourser ${money(amt, cur)} d'hypothèque`)
              }}>Rembourser ce que je peux</button>
            </div>
          ))}
        </div>
      )}
      {tab === 'study' && (
        <div className="panel">
          <p className="muted">
            Une maîtrise à l'étranger : {money(p.study_year, cur)} de frais par an (payés en devises, ils suivent le change),
            pas de salaire pendant les études, puis un salaire d'environ {Math.round(p.study_premium * 100)} % plus élevé. Une seule fois, jusqu'à {p.study_max_age} ans.
          </p>
          {canStudy ? (
            <div className="row">
              {[1, 2].map((y) => (
                <button key={y} disabled={full} onClick={() => add({ type: 'study', years: y }, `Étudier ${y} an(s) à l'étranger (${money(p.study_year * y, cur)})`)}>
                  {y} an{y > 1 ? 's' : ''} · {money(p.study_year * y, cur)}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">{v.studied ? 'Vous avez déjà fait vos études à l\'étranger.' : 'Ce n\'est plus possible dans votre situation.'}</p>
          )}
        </div>
      )}
      {tab === 'business' && (
        <div className="panel">
          {v.business ? (
            <>
              <p className="muted">
                Votre entreprise vaut {money(v.business.value, cur)} et vous verse environ {money(v.business.value * p.business_yield, cur)} par an.
                Elle peut faire faillite ou recevoir une offre de rachat.
              </p>
              <button disabled={full} onClick={() => add({ type: 'sell_business' }, `Vendre l'entreprise (${money(v.business.value, cur)})`)}>Vendre l'entreprise</button>
            </>
          ) : (
            <>
              <p className="muted">
                Vous quittez votre emploi pour vous lancer. Le bénéfice remplace votre salaire. Minimum {money(p.business_min, cur)}.
                Beaucoup d'entreprises ne passent pas cinq ans.
              </p>
              <AmountPicker label={`Capital investi (${cur})`} base={avail} full={full} min={p.business_min}
                onAdd={(n) => add({ type: 'start_business', amount: n }, `Créer une entreprise (${money(n, cur)})`)} />
            </>
          )}
        </div>
      )}
      {tab === 'rebalance' && <Rebalance v={v} add={add} full={full} />}
      {tab === 'give' && (
        <div className="panel">
          <p className="muted">À une cause, à des proches. Vous avez donné {money(v.given ?? 0, cur)} jusqu'ici.</p>
          <AmountPicker label={`Montant (${cur})`} base={avail} shortcuts={[0.01, 0.05, 0.1]} full={full}
            onAdd={(n) => add({ type: 'give', amount: n }, `Donner ${money(n, cur)}`)} />
        </div>
      )}
    </div>
  )
}

// Niveau Avancé : une part cible en ETF, rééquilibrée automatiquement chaque année.
function Rebalance({ v, add, full }) {
  const [share, setShare] = useState(Math.round((v.target ?? 0.6) * 100))
  const cur = v.country.currency
  const total = Math.max(v.available, 0) + v.etf
  return (
    <div className="panel">
      <p className="muted">
        Choisissez la part de votre argent placée en ETF ; le reste est gardé en liquidités (le fonds d'urgence n'est pas compté).
        Chaque année, achats ou ventes ramènent automatiquement la répartition vers votre cible.
      </p>
      <p>{v.target == null ? 'Aucune répartition automatique pour l\'instant.' : `Cible actuelle : ${Math.round(v.target * 100)} % en ETF.`}
        {' '}<span className="muted">Aujourd'hui : {total > 0 ? Math.round((v.etf / total) * 100) : 0} % en ETF.</span></p>
      <label>
        Part en ETF : {share} % · soit {money(total * share / 100, cur)} en ETF et {money(total * (100 - share) / 100, cur)} en liquidités
        <input type="range" min="0" max="100" step="10" value={share} onChange={(e) => setShare(Number(e.target.value))} />
      </label>
      <div className="row">
        <button disabled={full} onClick={() => add({ type: 'rebalance', etf_share: share / 100 }, `Répartition : ${share} % en ETF`)}>Appliquer chaque année</button>
        {v.target != null && <button disabled={full} onClick={() => add({ type: 'rebalance', etf_share: null }, 'Arrêter la répartition automatique')}>Arrêter</button>}
      </div>
    </div>
  )
}

// Composantes positives empilées sous la courbe du patrimoine net (la dette n'est pas empilée).
const LAYERS = [['cash', 'Liquidités'], ['etf', 'ETF'], ['property', 'Immobilier net'], ['business', 'Entreprise']]

function Chart({ points, start, height = 220, W = 600 }) {
  if (points.length < 2) return <p className="muted small">Le graphique apparaîtra après la première année.</p>
  const H = height, P = 40
  const xs = points.map((p) => p.age)
  const tops = points.map((p) => LAYERS.reduce((s, [k]) => s + Math.max(p[k] ?? 0, 0), 0))
  const ys = points.map((p) => p.net_worth_ppp)
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const [y0, y1] = [Math.min(0, ...ys), Math.max(...ys, ...tops, start ?? 1)]
  const X = (x) => P + ((x - x0) / Math.max(x1 - x0, 1)) * (W - 2 * P)
  const Y = (y) => H - P / 2 - ((y - y0) / (y1 - y0)) * (H - 1.5 * P)
  const pts = (arr) => arr.map((y, i) => `${X(xs[i]).toFixed(1)},${Y(y).toFixed(1)}`)
  const short = (y) => new Intl.NumberFormat('fr-CA', { notation: 'compact', maximumFractionDigits: 1 }).format(y) + ' $'
  let base = points.map(() => 0)
  const areas = LAYERS.map(([k]) => {
    const top = base.map((b, i) => b + Math.max(points[i][k] ?? 0, 0))
    const poly = [...pts(top), ...pts(base).reverse()].join(' ')
    base = top
    return <polygon key={k} points={poly} className={`area ${k}`} />
  })
  const step = (W - 2 * P) / Math.max(x1 - x0, 1)
  return (
    <figure className="chart-wrap">
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Trajectoire du patrimoine net et de sa composition, en pouvoir d'achat">
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line x1={P} x2={W - P} y1={Y(y0 + f * (y1 - y0))} y2={Y(y0 + f * (y1 - y0))} className="grid-line" />
            {f < 1 && <text x={4} y={Y(y0 + f * (y1 - y0)) + 4} className="tick">{short(y0 + f * (y1 - y0))}</text>}
          </g>
        ))}
        {areas}
        {points.map((p, i) => p.family && (
          <line key={i} x1={X(p.age)} x2={X(p.age)} y1={P / 2} y2={Y(y0)} className={`event-mark ${p.family}`} />
        ))}
        {start != null && <line x1={P} x2={W - P} y1={Y(start)} y2={Y(start)} className="start-line" />}
        {y0 < 0 && <line x1={P} x2={W - P} y1={Y(0)} y2={Y(0)} className="zero" />}
        <polyline points={pts(ys).join(' ')} className="line" />
        {points.map((p, i) => p.decided && <circle key={i} cx={X(p.age)} cy={Y(p.net_worth_ppp)} r="6" className="decision" />)}
        {points.map((p, i) => (
          <rect key={i} x={X(p.age) - step / 2} y={0} width={step} height={H} className="hit">
            <title>{[`${p.age} ans · ${money(p.net_worth_ppp, 'USD')}`, p.event, ...(p.log ?? [])].filter(Boolean).join('\n')}</title>
          </rect>
        ))}
        <text x={P} y={H - 4} className="tick">{x0} ans</text>
        <text x={W - P} y={H - 4} className="tick" textAnchor="end">{x1} ans</text>
        <text x={4} y={Y(y1) + 4} className="tick">{short(y1)}</text>
        <text x={4} y={Y(y0)} className="tick">{short(y0)}</text>
      </svg>
      <figcaption className="legend small">
        <span><i className="line" />Patrimoine net</span>
        <span><i className="decision" />Vos décisions</span>
        {start != null && <span><i className="start-line" />Montant de départ</span>}
        <span><i className="event-mark" />Événements</span>
        {LAYERS.map(([k, l]) => <span key={k}><i className={`area ${k}`} />{l}</span>)}
        <span className="muted">Survolez une année pour le détail.</span>
      </figcaption>
    </figure>
  )
}

// Facteurs de l'économie : la vraie année passée rejouée, chocs d'événements compris.
const ECONOMY = [
  ['Bourse', "ce qu'a rapporté l'ETF, après inflation", (e) => e.economy.stocks_real, () => 0],
  ['Inflation', 'la hausse des prix', (e) => e.economy.inflation + e.shocks.inflation_add, (e) => e.shocks.inflation_add],
  ['Épargne', 'ce que rapportent vos liquidités, après inflation', (e) => e.economy.cash_real + e.shocks.rate_add, (e) => e.shocks.rate_add],
  ['Dollar US', "s'il monte, voyages et études à l'étranger coûtent plus cher", (e) => e.economy.fx_real + e.shocks.fx_add, (e) => e.shocks.fx_add],
  ['Immobilier', 'le prix des logements, après inflation', (e) => e.economy.home_real + e.shocks.home_add, (e) => e.shocks.home_add],
]

// 1c : la variation du patrimoine, part par part (en pouvoir d'achat).
const PARTS = [
  ['decisions', 'Vos décisions'], ['event', 'Événements'], ['stocks', 'Bourse (ETF)'],
  ['property', 'Immobilier'], ['savings', 'Intérêts de l\'épargne'], ['rest', 'Revenus, dépenses et le reste'],
]
const signed = (x) => (x > 0 ? '+' : x < 0 ? '−' : '') + money(Math.abs(x), 'USD')

// Petits graphiques en barres, alignés sur l'âge comme le graphique du patrimoine (même W et P).
function Economy({ points, W = 600 }) {
  const pts = points.filter((p) => p.economy && p.breakdown) // shortcut: une API pas encore relancée n'envoie pas ces séries
  if (!pts.length) return null
  const H = 46, P = 40
  const last = pts[pts.length - 1]
  const total = Object.fromEntries(PARTS.map(([k]) => [k, pts.reduce((s, p) => s + p.breakdown[k], 0)]))
  const sum = (b) => PARTS.reduce((s, [k]) => s + b[k], 0)
  const [x0, x1] = [pts[0].age, last.age]
  const X = (x) => P + ((x - x0) / Math.max(x1 - x0, 1)) * (W - 2 * P)
  const step = Math.min((W - 2 * P) / Math.max(x1 - x0, 1), 40)
  const tone = (x) => (Math.abs(x) < 0.5 ? 'muted' : x > 0 ? 'up' : 'down')
  return (
    <details className="economy" open>
      <summary>L'économie de votre vie</summary>
      <h4>Ce qui a fait bouger votre patrimoine</h4>
      <table className="parts small">
        <thead><tr><th /><th>À {last.age} ans</th><th>Depuis le début</th></tr></thead>
        <tbody>
          {PARTS.filter(([k]) => Math.abs(total[k]) >= 0.5).map(([k, l]) => (
            <tr key={k}><th>{l}</th><td className={tone(last.breakdown[k])}>{signed(last.breakdown[k])}</td><td className={tone(total[k])}>{signed(total[k])}</td></tr>
          ))}
        </tbody>
        <tfoot><tr><th>Variation du patrimoine</th><td className={tone(sum(last.breakdown))}>{signed(sum(last.breakdown))}</td><td className={tone(sum(total))}>{signed(sum(total))}</td></tr></tfoot>
      </table>
      <h4>L'économie, année après année</h4>
      <p className="muted small">Chaque année de jeu rejoue une vraie année passée de votre pays. Survolez une barre pour savoir laquelle.</p>
      {ECONOMY.map(([label, help, get, shock]) => {
        const vals = pts.map(get)
        const m = Math.max(...vals.map(Math.abs), 0.01)
        const Y = (v) => H / 2 - (v / m) * (H / 2 - 2)
        return (
          <figure key={label} className="mini">
            <figcaption className="small"><strong>{label}</strong> : {help}. <span className="muted">À {last.age} ans : {pct(vals[vals.length - 1])}</span></figcaption>
            <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${label}, année par année`}>
              <line x1={P} x2={W - P} y1={H / 2} y2={H / 2} className="grid-line" />
              {pts.map((p, i) => (
                <rect key={i} x={X(p.age) - step * 0.35} width={step * 0.7} y={Math.min(Y(vals[i]), H / 2)} height={Math.max(Math.abs(Y(vals[i]) - H / 2), 1)} className="bar" />
              ))}
              {pts.map((p, i) => (
                <rect key={'h' + i} x={X(p.age) - step / 2} y={0} width={step} height={H} className="hit">
                  <title>{`${p.age} ans : ${pct(vals[i])} (comme en ${p.market_year})`
                    + (shock(p) ? `\ndont ${pct(shock(p))} dû à un événement` : '')}</title>
                </rect>
              ))}
            </svg>
          </figure>
        )
      })}
    </details>
  )
}

// Une phrase neutre par axe : [côté gauche, milieu, côté droit].
const AXES = [
  ['vivre_batir', 'Vivre', 'Bâtir', [
    'Vous avez mis une bonne part de l\'argent dans des moments vécus.',
    'Vous avez partagé entre profiter et construire.',
    'Vous avez surtout fait fructifier l\'argent.']],
  ['securite_aventure', 'Sécurité', 'Aventure', [
    'Vous avez gardé l\'argent à l\'abri des secousses.',
    'Vous avez pris des risques mesurés.',
    'Vous avez accepté les montagnes russes.']],
  ['moi_autres', 'Moi', 'Les autres', [
    'L\'argent a surtout servi vos propres projets.',
    'Vous avez dépensé pour vous et donné à d\'autres, dans des proportions voisines.',
    'Une part importante est allée à d\'autres que vous.']],
  ['racines_ailleurs', 'Racines', 'Ailleurs', [
    'Votre vie s\'est déroulée près de chez vous.',
    'Vous êtes parti·e de temps en temps.',
    'Vous avez souvent vécu ou voyagé ailleurs.']],
]

function Axis({ left, right, value, sentences }) {
  const sentence = sentences[value < -0.33 ? 0 : value > 0.33 ? 2 : 1]
  return (
    <div className="axis-block">
      <div className="axis" role="img" aria-label={`${left} ↔ ${right} : ${sentence}`}>
        <span>{left}</span>
        <div className="bar"><i style={{ left: `${((value + 1) / 2) * 100}%` }} /></div>
        <span>{right}</span>
      </div>
      <p className="muted small">{sentence}</p>
    </div>
  )
}

function Mirror({ v, level, onReplay, onNew, seed }) {
  const m = v.mirror
  const c = v.country
  const [copied, setCopied] = useState(false)
  return (
    <section className="card mirror">
      <p className="eyebrow">Miroir · {c.name}, de {v.start_age} à {v.age} ans</p>
      <h2>Votre vie s'achève à {v.age} ans.</h2>
      <p className="muted">Patrimoine net au fil des années, en pouvoir d'achat (dollars US équivalents).</p>
      <Chart points={v.history} start={v.prize_local / c.ppp} />
      {level === 'avance' && <Economy points={v.history} />}
      <dl className="stats">
        <div><dt>Patrimoine laissé</dt><dd>{money(m.final_net_worth_ppp, 'USD')}</dd></div>
        <div><dt>Au plus haut</dt><dd>{money(m.peak_net_worth_ppp, 'USD')}</dd></div>
        <div><dt>Années de liberté financière</dt><dd>{m.freedom_years} / {m.years}</dd></div>
        <div><dt>Voyages</dt><dd>{m.trips}</dd></div>
        <div><dt>Argent donné</dt><dd>{money(m.given_ppp, 'USD')}</dd></div>
      </dl>
      <h3>Votre style</h3>
      <p className="muted">Ni bon ni mauvais : une façon de faire parmi d'autres.</p>
      {AXES.map(([key, left, right, sentences]) => (
        <Axis key={key} left={left} right={right} value={m[key]} sentences={sentences} />
      ))}
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
