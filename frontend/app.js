const API = window.PAYSENTRY_API || 'http://127.0.0.1:8000';
let timelineCache = [];

const $ = (id) => document.getElementById(id);
const money = (value) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 0
}).format(value || 0);

function setError(message = '') {
  const el = $('error');
  el.textContent = message;
  el.classList.toggle('hidden', !message);
}

function renderChart(timeline = []) {
  if (!timeline.length) return;
  timelineCache = timeline;
  const w = 760, h = 180;
  const points = timeline.map((d, i) => {
    const x = (i / Math.max(timeline.length - 1, 1)) * w;
    const y = h - ((d.success_rate - 40) / 60) * h;
    return `${x.toFixed(1)},${Math.max(0, Math.min(h, y)).toFixed(1)}`;
  }).join(' ');
  $('trend').setAttribute('points', points);
}

function render(data) {
  $('baseline').textContent = `${data.baseline_success_rate}%`;
  $('current').textContent = `${data.current_success_rate}%`;
  $('drop').textContent = `${data.drop_percentage_points} pp`;
  $('revenue').textContent = money(data.revenue_at_risk);

  const severity = $('severity');
  severity.textContent = data.severity;
  severity.className = `sev ${data.severity}`;

  $('headline').textContent = data.incident_detected ? 'Payment incident detected' : 'Systems operating normally';
  $('explanation').textContent = data.explanation;
  $('rootCause').textContent = data.likely_root_cause || 'None';
  $('confidence').textContent = `${data.confidence}%`;
  $('method').textContent = data.affected_method || '—';
  $('bank').textContent = data.affected_bank || '—';
  $('region').textContent = data.affected_region || '—';
  $('impacted').textContent = data.transactions_impacted;

  const list = $('recommendations');
  list.replaceChildren();
  data.recommendation.forEach((item, index) => {
    const li = document.createElement('li');
    const badge = document.createElement('span');
    badge.textContent = String(index + 1);
    li.append(badge, document.createTextNode(item));
    list.appendChild(li);
  });

  if (data.timeline?.length) renderChart(data.timeline);
  else if (timelineCache.length) renderChart(timelineCache);
}

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(`API returned HTTP ${response.status}`);
  return response.json();
}

async function loadDemo() {
  setError();
  try {
    render(await request(`${API}/api/v1/demo`));
  } catch (error) {
    setError(`Could not reach PaySentry API: ${error.message}`);
  }
}

async function runScenario() {
  const button = $('runBtn');
  button.disabled = true;
  button.textContent = 'Analyzing…';
  setError();
  try {
    const result = await request(`${API}/api/v1/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        incident_type: $('scenario').value,
        minutes: 120,
        transactions_per_minute: 35,
        seed: 42
      })
    });
    render(result);
  } catch (error) {
    setError(`Analysis failed: ${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = 'Run AI analysis';
  }
}

$('runBtn').addEventListener('click', runScenario);
loadDemo();
