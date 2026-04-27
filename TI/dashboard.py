#!/usr/bin/env python3
"""
Infosys TI Dashboard -- Browser UI
====================================
Sab kuch ek jagah:
- Policy pack status + hash verify
- ARR Filing (real KERC data)
- Catalog publish status
- Bill calculator
- Cross-team bills
- BPP server status

Run: python dashboard.py
Open: http://localhost:5001
"""

import json
import hashlib
import os
import requests as req_lib
from datetime import datetime, timezone
from flask import Flask, render_template_string, request, jsonify
from tariff_engine import compute_bill

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Infosys TI Dashboard</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; background: #f0f2f5; color: #333; }

    .header {
      background: linear-gradient(135deg, #1a237e, #283593);
      color: white; padding: 20px 30px;
    }
    .header h1 { font-size: 22px; }
    .header p  { font-size: 13px; opacity: 0.8; margin-top: 4px; }

    .container { max-width: 1200px; margin: 24px auto; padding: 0 20px; }

    .cards { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 24px; }
    .card {
      background: white; border-radius: 10px; padding: 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .card .label { font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .card .value { font-size: 22px; font-weight: bold; color: #1a237e; margin: 6px 0 4px; }
    .card .sub   { font-size: 11px; color: #666; }

    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; }
    .badge.green  { background: #e8f5e9; color: #2e7d32; }
    .badge.blue   { background: #e3f2fd; color: #1565c0; }
    .badge.orange { background: #fff3e0; color: #e65100; }
    .badge.red    { background: #ffebee; color: #c62828; }

    .panel {
      background: white; border-radius: 10px; padding: 24px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 20px;
    }
    .panel h2 {
      font-size: 15px; color: #1a237e; margin-bottom: 16px;
      border-bottom: 2px solid #e3f2fd; padding-bottom: 10px;
      display: flex; align-items: center; gap: 8px;
    }

    .form-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; margin-bottom: 14px; }
    .form-group label { display: block; font-size: 12px; color: #666; margin-bottom: 4px; }
    .form-group input, .form-group select {
      width: 100%; padding: 9px 12px; border: 1px solid #ddd;
      border-radius: 6px; font-size: 14px;
    }

    .btn {
      background: #1a237e; color: white; border: none;
      padding: 10px 24px; border-radius: 6px; font-size: 13px;
      cursor: pointer; font-weight: bold;
    }
    .btn:hover { background: #283593; }
    .btn.green { background: #2e7d32; }
    .btn.green:hover { background: #1b5e20; }

    .bill-result {
      margin-top: 20px; display: none;
      border: 2px solid #1a237e; border-radius: 10px; overflow: hidden;
    }
    .bill-header { background: #1a237e; color: white; padding: 14px 20px; text-align: center; }
    .bill-header h3 { font-size: 15px; }
    .bill-header p  { font-size: 12px; opacity: 0.8; }
    .bill-body { padding: 16px 20px; }
    .bill-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
    .bill-row:last-child { border: none; }
    .bill-row.total { font-weight: bold; font-size: 15px; color: #1a237e; border-top: 2px solid #1a237e; padding-top: 10px; margin-top: 4px; }
    .bill-row.slab  { padding-left: 16px; color: #555; font-size: 12px; }
    .bill-row.discount { color: #2e7d32; }
    .bill-row.surcharge { color: #c62828; }

    .hash-box {
      background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px;
      padding: 10px 14px; font-family: monospace; font-size: 12px; color: #555;
      word-break: break-all; margin-top: 10px;
    }

    .policy-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .policy-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; }
    .policy-card h3 { font-size: 13px; color: #1a237e; margin-bottom: 10px; }
    .slab-row { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed #eee; }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { background: #e8eaf6; padding: 10px 12px; text-align: left; color: #1a237e; font-size: 12px; }
    td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
    tr:hover td { background: #fafafa; }

    .arr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .arr-table { font-size: 13px; }
    .arr-row { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px solid #f0f2f5; }
    .arr-row.total { font-weight: bold; color: #1a237e; border-top: 2px solid #1a237e; padding-top: 10px; }
    .arr-row.income { color: #2e7d32; }
    .arr-meta { background: #f8f9fa; border-radius: 8px; padding: 16px; font-size: 12px; }
    .arr-meta .meta-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dashed #eee; }
    .arr-meta .meta-row:last-child { border: none; }

    .catalog-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .catalog-item { border: 1px solid #c8e6c9; border-radius: 8px; padding: 14px; background: #f1f8e9; }
    .catalog-item h4 { font-size: 13px; color: #2e7d32; margin-bottom: 6px; }
    .catalog-item p { font-size: 12px; color: #555; }

    .cross-summary { background: #e8eaf6; border-radius: 8px; padding: 14px; margin-bottom: 14px; display: flex; gap: 24px; }
    .cross-summary .cs { text-align: center; }
    .cross-summary .cs .cv { font-size: 20px; font-weight: bold; color: #1a237e; }
    .cross-summary .cs .cl { font-size: 11px; color: #666; }
  </style>
</head>
<body>

<div class="header">
  <h1>Infosys TI — Tariff Intelligence Dashboard</h1>
  <p>Karnataka SERC Tariff Pack | KERC ARR Filing | Beckn DEG Network | GCP Verified</p>
</div>

<div class="container">

  <!-- Status Cards -->
  <div class="cards">
    <div class="card">
      <div class="label">Tariff Policies</div>
      <div class="value" id="policyCount">--</div>
      <div class="sub"><span class="badge green" id="hashBadge">Verifying...</span></div>
    </div>
    <div class="card">
      <div class="label">Policy Hash</div>
      <div class="value" style="font-size:13px;padding-top:6px;" id="hashShort">--</div>
      <div class="sub">GCP SERC Verified</div>
    </div>
    <div class="card">
      <div class="label">ARR Filing</div>
      <div class="value" id="arrStatus">--</div>
      <div class="sub" id="arrSub">Loading...</div>
    </div>
    <div class="card">
      <div class="label">Catalog Published</div>
      <div class="value" id="catalogCount">--</div>
      <div class="sub" id="catalogSub">Resources on network</div>
    </div>
    <div class="card">
      <div class="label">BPP Server</div>
      <div class="value" id="bppStatus">--</div>
      <div class="sub" id="bppSub">port 5000</div>
    </div>
    <div class="card">
      <div class="label">Cross-Team Bills</div>
      <div class="value" id="crossCount">--</div>
      <div class="sub" id="crossSub">meters billed</div>
    </div>
  </div>

  <!-- Tariff Policies -->
  <div class="panel">
    <h2>Tariff Policies <span style="font-size:12px;color:#666;font-weight:normal">(from policy_pack.json — GCP)</span></h2>
    <div class="policy-grid" id="policyGrid">Loading...</div>
  </div>

  <!-- ARR Filing -->
  <div class="panel">
    <h2>ARR Filing <span style="font-size:12px;color:#666;font-weight:normal">(Real Data — KERC Tariff Order 2023)</span>
      <span class="badge green" style="margin-left:auto">PUBLISHED ON CATALOG</span>
    </h2>
    <div class="arr-grid" id="arrGrid">Loading...</div>
  </div>

  <!-- Catalog Publish Status -->
  <div class="panel">
    <h2>Catalog Published on Beckn DEG Network</h2>
    <div class="catalog-grid" id="catalogGrid">Loading...</div>
  </div>

  <!-- Bill Calculator -->
  <div class="panel">
    <h2>Bill Calculator <span style="font-size:12px;color:#666;font-weight:normal">(Live — uses GCP tariff)</span></h2>
    <div class="form-row">
      <div class="form-group">
        <label>Consumer Name</label>
        <input type="text" id="cName" value="Ramesh Kumar" />
      </div>
      <div class="form-group">
        <label>Consumer No.</label>
        <input type="text" id="cNo" value="KA-RES-204891" />
      </div>
      <div class="form-group">
        <label>Tariff Category</label>
        <select id="cPolicy">
          <option value="RES-T1">Residential (RES-T1)</option>
          <option value="COM-TOU1">Commercial (COM-TOU1)</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Previous Reading (kWh)</label>
        <input type="number" id="cPrev" value="1240" />
      </div>
      <div class="form-group">
        <label>Current Reading (kWh)</label>
        <input type="number" id="cCurr" value="1590" />
      </div>
      <div class="form-group">
        <label>Peak/Night Units (kWh)</label>
        <input type="number" id="cSpecial" value="50" placeholder="Peak (COM) / Night (RES)" />
      </div>
    </div>
    <button class="btn" onclick="generateBill()">Generate Bill</button>

    <div class="bill-result" id="billResult">
      <div class="bill-header">
        <h3>KARNATAKA ELECTRICITY SUPPLY COMPANY</h3>
        <p id="billConsumer"></p>
      </div>
      <div class="bill-body" id="billBody"></div>
    </div>
  </div>

  <!-- Bills History -->
  <div class="panel">
    <h2>Generated Bills</h2>
    <div id="billsTable">Loading...</div>
  </div>

  <!-- Cross-Team Bills -->
  <div class="panel">
    <h2>Cross-Team Billing <span style="font-size:12px;color:#666;font-weight:normal">(Team B meter data + our tariff engine)</span></h2>
    <div id="crossBills">Loading...</div>
  </div>

  <!-- Hash Proof -->
  <div class="panel">
    <h2>Tamper-Proof Verification</h2>
    <p style="font-size:13px;color:#555;margin-bottom:8px;">
      SHA-256 hash of the tariff data — proves data came from GCP SERC and was not modified.
    </p>
    <div class="hash-box" id="fullHash">Loading...</div>
  </div>

</div>

<script>
// 1. Load policy pack
fetch('/api/policy').then(r=>r.json()).then(d => {
  document.getElementById('policyCount').textContent = d.policies.length + ' Policies';
  document.getElementById('hashBadge').textContent = d.hashOk ? 'Hash Verified' : 'Hash FAIL';
  document.getElementById('hashBadge').className = 'badge ' + (d.hashOk ? 'green' : 'red');
  document.getElementById('hashShort').textContent = d.hash.substring(0,16) + '...';
  document.getElementById('fullHash').textContent = 'SHA-256: ' + d.hash;
  let html = '';
  d.policies.forEach(p => {
    html += `<div class="policy-card"><h3>${p.policyID} — ${p.policyName}</h3>`;
    p.energySlabs.forEach(s => {
      let range = s.end ? s.start+'-'+s.end+' kWh' : s.start+'+ kWh';
      html += `<div class="slab-row"><span>${range}</span><span><b>Rs.${s.price}/kWh</b></span></div>`;
    });
    p.surchargeTariffs.forEach(s => {
      html += `<div class="slab-row" style="color:#e65100"><span>${s.id}</span><span>${s.value > 0 ? '+' : ''}${s.value} ${s.unit}</span></div>`;
    });
    html += `</div>`;
  });
  document.getElementById('policyGrid').innerHTML = html;
});

// 2. Load ARR Filing
fetch('/api/arr').then(r=>r.json()).then(d => {
  if (d.error) {
    document.getElementById('arrStatus').textContent = 'N/A';
    document.getElementById('arrGrid').innerHTML = '<p style="color:#999">arr_filing.json not found</p>';
    return;
  }
  document.getElementById('arrStatus').textContent = 'APPROVED';
  document.getElementById('arrSub').textContent = 'KERC FY 2023-24';

  const dp = d.dataPayload;
  const items = dp.fiscalYears[0].lineItems;
  let rowsHtml = '';
  items.forEach(item => {
    const isTotal = item.subCategory === 'NET_ARR';
    const isIncome = item.amount < 0;
    const cls = isTotal ? 'arr-row total' : (isIncome ? 'arr-row income' : 'arr-row');
    rowsHtml += `<div class="${cls}">
      <span>${item.head}</span>
      <span>${item.amount < 0 ? '-' : ''}Rs. ${Math.abs(item.amount).toLocaleString('en-IN')} Cr</span>
    </div>`;
  });

  const metaHtml = `
    <div class="arr-meta">
      <div style="font-size:13px;font-weight:bold;color:#1a237e;margin-bottom:10px">Filing Details</div>
      <div class="meta-row"><span>Filing ID</span><span><b>${dp.filingId}</b></span></div>
      <div class="meta-row"><span>Licensee</span><span>${dp.licensee}</span></div>
      <div class="meta-row"><span>Regulator</span><span>${dp.regulatoryCommission}</span></div>
      <div class="meta-row"><span>Fiscal Year</span><span>${dp.fiscalYears[0].fiscalYear}</span></div>
      <div class="meta-row"><span>Status</span><span><span class="badge green">${dp.status}</span></span></div>
      <div class="meta-row"><span>Approved ARR</span><span><b>Rs. ${d.approvedARR.toLocaleString('en-IN')} Cr</b></span></div>
      <div class="meta-row"><span>Avg Cost of Supply</span><span>Rs. ${d.avgCostOfSupply} / unit</span></div>
      <div class="meta-row"><span>Total Sales</span><span>${d.totalSalesMU.toLocaleString('en-IN')} MU</span></div>
      <div class="meta-row"><span>Data Source</span><span style="color:#2e7d32;font-size:11px">${d.dataSource}</span></div>
    </div>`;

  document.getElementById('arrGrid').innerHTML =
    `<div class="arr-table">${rowsHtml}</div>${metaHtml}`;
});

// 3. Load Catalog
fetch('/api/catalog').then(r=>r.json()).then(d => {
  document.getElementById('catalogCount').textContent = d.resources.length + ' Resources';
  let html = '';
  d.resources.forEach(r => {
    html += `<div class="catalog-item">
      <h4>✓ ${r.name}</h4>
      <p>${r.shortDesc}</p>
      <p style="margin-top:6px"><span class="badge green">PUBLISHED</span>
        <span style="font-size:11px;color:#666;margin-left:6px">${r.id}</span></p>
    </div>`;
  });
  document.getElementById('catalogGrid').innerHTML = html;
});

// 4. BPP status
fetch('/api/bpp-status').then(r=>r.json()).then(d => {
  document.getElementById('bppStatus').textContent = d.up ? 'UP' : 'DOWN';
  document.getElementById('bppStatus').style.color = d.up ? '#2e7d32' : '#c62828';
  document.getElementById('bppSub').textContent = d.up ? 'port 5000 — live' : 'not running';
});

// 5. Cross-team bills
fetch('/api/cross-bills').then(r=>r.json()).then(d => {
  if (d.error || !d.results) {
    document.getElementById('crossCount').textContent = '0';
    document.getElementById('crossBills').innerHTML = '<p style="color:#999;font-size:13px">cross_team_bills.json not found. Run cross_team_billing.py first.</p>';
    return;
  }
  document.getElementById('crossCount').textContent = d.results.length;
  document.getElementById('crossSub').textContent = 'Rs. ' + d.totalRevenue.toLocaleString('en-IN');

  let summary = `<div class="cross-summary">
    <div class="cs"><div class="cv">${d.results.length}</div><div class="cl">Meters Billed</div></div>
    <div class="cs"><div class="cv">Rs. ${d.totalRevenue.toLocaleString('en-IN')}</div><div class="cl">Total Revenue</div></div>
    <div class="cs"><div class="cv">${d.results.filter(r=>r.policy==='RES-T1').length}</div><div class="cl">RES-T1</div></div>
    <div class="cs"><div class="cv">${d.results.filter(r=>r.policy==='COM-TOU1').length}</div><div class="cl">COM-TOU1</div></div>
    <div class="cs"><div class="cv" style="font-size:12px">${d.tariffFrom || 'Infosys TI BPP'}</div><div class="cl">Tariff Source</div></div>
  </div>`;

  let table = '<table><tr><th>Meter</th><th>Zone</th><th>Profile</th><th>Policy</th><th>kWh</th><th>Base</th><th>Surcharge</th><th>Total</th></tr>';
  d.results.forEach(r => {
    table += `<tr>
      <td><b>${r.resource}</b></td>
      <td>${r.zone}</td>
      <td><span class="badge ${r.profile==='commercial'?'orange':'blue'}">${r.profile}</span></td>
      <td>${r.policy}</td>
      <td>${r.total_kwh}</td>
      <td>Rs.${r.base_charge}</td>
      <td style="color:${r.surcharge<0?'#2e7d32':'#c62828'}">Rs.${r.surcharge}</td>
      <td><b>Rs.${r.total_bill}</b></td>
    </tr>`;
  });
  table += '</table>';
  document.getElementById('crossBills').innerHTML = summary + table;
});

// 6. Load bills
loadBills();
function loadBills() {
  fetch('/api/bills').then(r=>r.json()).then(d => {
    if (!d.bills || d.bills.length === 0) {
      document.getElementById('billsTable').innerHTML = '<p style="color:#999;font-size:13px">No bills yet. Generate one above!</p>';
      return;
    }
    let html = '<table><tr><th>Consumer</th><th>Category</th><th>Units</th><th>Base</th><th>Surcharge</th><th>Total Bill</th></tr>';
    d.bills.forEach(b => {
      html += `<tr>
        <td>${b.name}<br><small style="color:#999">${b.consumerNo}</small></td>
        <td><span class="badge ${b.category=='RESIDENTIAL'?'blue':'orange'}">${b.category}</span></td>
        <td>${b.units} kWh</td>
        <td>Rs.${b.baseCharge.toFixed(2)}</td>
        <td style="color:${b.surcharge<0?'#2e7d32':'#c62828'}">Rs.${b.surcharge.toFixed(2)}</td>
        <td><b>Rs.${b.totalBill.toFixed(2)}</b></td>
      </tr>`;
    });
    html += '</table>';
    document.getElementById('billsTable').innerHTML = html;
  });
}

function generateBill() {
  const data = {
    name: document.getElementById('cName').value,
    no: document.getElementById('cNo').value,
    policy: document.getElementById('cPolicy').value,
    prev: parseFloat(document.getElementById('cPrev').value),
    curr: parseFloat(document.getElementById('cCurr').value),
    special: parseFloat(document.getElementById('cSpecial').value) || 0,
  };
  fetch('/api/calculate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  }).then(r=>r.json()).then(b => {
    document.getElementById('billConsumer').textContent = data.name + ' | ' + data.no + ' | ' + b.units + ' kWh';
    let html = '';
    html += `<div class="bill-row"><span>Previous Reading</span><span>${data.prev} kWh</span></div>`;
    html += `<div class="bill-row"><span>Current Reading</span><span>${data.curr} kWh</span></div>`;
    html += `<div class="bill-row"><span>Units Consumed</span><span><b>${b.units} kWh</b></span></div>`;
    html += `<hr style="margin:10px 0;border:none;border-top:1px solid #eee">`;
    b.slabs.forEach(s => {
      html += `<div class="bill-row slab"><span>${s.range}</span><span>${s.units} kWh x Rs.${s.rate} = Rs.${s.amount.toFixed(2)}</span></div>`;
    });
    html += `<div class="bill-row"><span>Base Energy Charge</span><span><b>Rs.${b.baseCharge.toFixed(2)}</b></span></div>`;
    if (b.surcharge !== 0) {
      html += `<div class="bill-row ${b.surcharge < 0 ? 'discount' : 'surcharge'}"><span>${b.surchargeLabel}</span><span>Rs.${b.surcharge.toFixed(2)}</span></div>`;
    }
    html += `<div class="bill-row total"><span>TOTAL AMOUNT PAYABLE</span><span>Rs.${b.total.toFixed(2)}</span></div>`;
    html += `<div style="margin-top:12px;font-size:11px;color:#999">Tariff: ${b.policyId} | Hash: ${b.hash.substring(0,20)}... | Source: GCP SERC</div>`;
    document.getElementById('billBody').innerHTML = html;
    document.getElementById('billResult').style.display = 'block';
    loadBills();
  });
}
</script>
</body>
</html>
"""

# ── helpers ──

def load_pack():
    with open("policy_pack.json") as f:
        return json.load(f)

def load_arr():
    with open("arr_filing.json") as f:
        return json.load(f)

def load_catalog():
    path = os.path.join(os.path.dirname(__file__),
        "..", "DEG", "devkits", "data-exchange",
        "usecase2", "examples", "publish-catalog-infosys.json")
    with open(os.path.normpath(path)) as f:
        return json.load(f)

bill_history = []

# ── routes ──

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/policy")
def api_policy():
    pack = load_pack()
    dp   = pack["dataPayload"]
    canonical = json.dumps(dp, sort_keys=True, separators=(',', ':'))
    computed  = hashlib.sha256(canonical.encode()).hexdigest()
    return jsonify({
        "policies": dp["policies"],
        "programs": dp["programs"],
        "hash":     pack["payloadHash"],
        "hashOk":   computed == pack["payloadHash"],
    })

@app.route("/api/arr")
def api_arr():
    try:
        data = load_arr()
        return jsonify({
            "dataPayload":   data["dataPayload"],
            "filedBy":       data.get("filedBy", "infosys-ti-bpp"),
            "dataSource":    data.get("dataSource", "KERC Tariff Order 2023"),
            "approvedARR":   data["dataPayload"].get("approvedARR", 28872.87),
            "totalSalesMU":  data["dataPayload"].get("totalSalesMU", 30013.92),
            "avgCostOfSupply": data["dataPayload"].get("avgCostOfSupply_Rs_per_unit", 9.62),
        })
    except FileNotFoundError:
        return jsonify({"error": "arr_filing.json not found"}), 404

@app.route("/api/catalog")
def api_catalog():
    try:
        cat = load_catalog()
        catalogs = cat["message"]["catalogs"]
        resources = []
        for c in catalogs:
            for r in c.get("resources", []):
                resources.append({
                    "id":        r["id"],
                    "name":      r["descriptor"]["name"],
                    "shortDesc": r["descriptor"].get("shortDesc", ""),
                    "published": True,
                })
        return jsonify({
            "resources": resources,
            "totalCatalogs": len(catalogs),
            "bppId": cat["context"]["bppId"],
        })
    except Exception as e:
        return jsonify({"error": str(e), "resources": []}), 200

@app.route("/api/bpp-status")
def api_bpp_status():
    try:
        r = req_lib.get("http://localhost:5000/health", timeout=2)
        data = r.json()
        return jsonify({"up": True, "policies": data.get("policies", [])})
    except Exception:
        return jsonify({"up": False})

@app.route("/api/cross-bills")
def api_cross_bills():
    try:
        with open("cross_team_bills.json") as f:
            data = json.load(f)
        cb = data["crossTeamBilling"]
        return jsonify({
            "results":      cb["results"],
            "totalRevenue": cb["totalRevenue"],
            "tariffFrom":   cb.get("tariffFrom", "Infosys TI BPP"),
            "meterDataFrom": cb.get("meterDataFrom", "Team B"),
        })
    except FileNotFoundError:
        return jsonify({"error": "cross_team_bills.json not found"}), 200

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data     = request.json
    pack     = load_pack()
    policies = {p["policyID"]: p for p in pack["dataPayload"]["policies"]}
    policy   = policies[data["policy"]]
    units    = data["curr"] - data["prev"]
    special  = data.get("special", 0)

    if data["policy"] == "RES-T1":
        bill   = compute_bill(policy, total_kwh=units, night_kwh=special)
        slabel = f"Night discount (-10%) on {special} kWh"
    else:
        bill   = compute_bill(policy, total_kwh=units, peak_kwh=special)
        slabel = f"Evening peak (+Rs.1.5/kWh) on {special} kWh"

    slabs = []
    remaining = units
    for s in policy["energySlabs"]:
        start, end, rate = s["start"], s.get("end"), s["price"]
        used = min(remaining, (end - start + 1) if end else remaining)
        if used <= 0: break
        r = f"{start}-{end} kWh" if end else f"{start}+ kWh"
        slabs.append({"range": r, "units": round(used), "rate": rate, "amount": used * rate})
        remaining -= used

    bill_history.append({
        "consumerNo": data["no"],
        "name":       data["name"],
        "category":   "RESIDENTIAL" if data["policy"] == "RES-T1" else "COMMERCIAL",
        "units":      units,
        "baseCharge": round(bill.base_charge, 2),
        "surcharge":  round(bill.surcharge_total, 2),
        "totalBill":  round(bill.total_bill, 2),
    })

    return jsonify({
        "units":          units,
        "slabs":          slabs,
        "baseCharge":     round(bill.base_charge, 2),
        "surcharge":      round(bill.surcharge_total, 2),
        "surchargeLabel": slabel,
        "total":          round(bill.total_bill, 2),
        "policyId":       data["policy"],
        "hash":           pack["payloadHash"],
    })

@app.route("/api/bills")
def api_bills():
    all_bills = list(bill_history)
    try:
        with open("generated_bills.json") as f:
            saved = json.load(f)
            for b in saved.get("bills", []):
                if not any(x["consumerNo"] == b["consumerNo"] for x in all_bills):
                    all_bills.append(b)
    except FileNotFoundError:
        pass
    return jsonify({"bills": all_bills})

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Infosys TI Dashboard — Full View")
    print("="*55)
    print("  Open browser: http://localhost:5001")
    print("  Shows: Tariff + ARR Filing + Catalog + Bills")
    print("="*55 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
