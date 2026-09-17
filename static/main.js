async function postJSON(url, data){
  const token = localStorage.getItem('token')
  const headers = {'Content-Type':'application/json'}
  if(token) headers['Authorization'] = 'Bearer '+token
  const r = await fetch(url,{method:'POST',headers,body:JSON.stringify(data)})
  return r.json().then(j=>({status:r.status, body:j}))
}

// update nav based on auth state
function updateNavForAuth(){
  const token = localStorage.getItem('token')
  const login = document.getElementById('nav-login')
  const reg = document.getElementById('nav-register')
  const logout = document.getElementById('nav-logout')
  if(login) login.style.display = token ? 'none' : ''
  if(reg) reg.style.display = token ? 'none' : ''
  if(logout) logout.style.display = token ? '' : 'none'
}
document.addEventListener('DOMContentLoaded', updateNavForAuth)
// logout handler
document.addEventListener('click', function(e){
  if(e.target && e.target.id === 'nav-logout'){
    e.preventDefault(); localStorage.removeItem('token'); updateNavForAuth(); window.location = '/login'
  }
})

// Register
const regForm = document.getElementById('register-form')
if(regForm){
  regForm.addEventListener('submit', async e=>{
    e.preventDefault(); const fd=new FormData(regForm)
    const res = await postJSON('/api/auth/register',{username:fd.get('username'),password:fd.get('password')})
    const msg = document.getElementById('msg')
    msg.textContent = res.body.msg || 'Registered. Please login.'
  })
}

const loginForm = document.getElementById('login-form')
if(loginForm){
  loginForm.addEventListener('submit', async e=>{
    e.preventDefault(); const fd=new FormData(loginForm)
    const res = await postJSON('/api/auth/login',{username:fd.get('username'),password:fd.get('password')})
    const msg = document.getElementById('msg')
    if(res.status===200){localStorage.setItem('token', res.body.access_token); window.location='/dashboard'} else msg.textContent = res.body.msg || 'error'
  })
}

// Dashboard
if(document.getElementById('med-table')){
  let page=1; let sort='name'; let order='asc'; const limit=10; const tbody=document.querySelector('#med-table tbody')
  async function load(){
    const token=localStorage.getItem('token');
    const q=document.getElementById('search').value||''
    let url
    if(q && q.length>0){
      url = `/api/medicines/search?q=${encodeURIComponent(q)}&page=${page}&limit=${limit}&sort=${encodeURIComponent(sort)}&order=${encodeURIComponent(order)}`
    } else {
      url = `/api/medicines?page=${page}&limit=${limit}&sort=${encodeURIComponent(sort)}&order=${encodeURIComponent(order)}`
    }
    const r = await fetch(url,{headers:{'Authorization':'Bearer '+token}})
    if(r.status===401){window.location='/login';return}
    const data = await r.json()
    document.getElementById('page').textContent=page
    document.getElementById('total-meds').textContent = data.total
    tbody.innerHTML=''
    data.items.forEach(m=>{
      const tr=document.createElement('tr')
      tr.innerHTML = `<td><a href="/medicines/${m.id}">${m.name}</a></td><td>${m.generic_name||''}</td><td>${m.manufacturer||''}</td><td>${m.sellable_stock}</td>`
      tbody.appendChild(tr)
    })
  }
  async function loadSummary(){
    const token=localStorage.getItem('token');
    const r = await fetch('/api/dashboard/summary',{headers:{'Authorization':'Bearer '+token}})
    if(r.status===401){window.location='/login';return}
    const d = await r.json()
    document.getElementById('total-meds').textContent = d.total_medicines
    document.getElementById('total-stock').textContent = d.total_sellable_stock
    document.getElementById('expiring-soon').textContent = d.expiring_soon_count
  }
  document.getElementById('next').addEventListener('click',()=>{page++;load()})
  document.getElementById('prev').addEventListener('click',()=>{if(page>1)page--;load()})
  document.getElementById('search').addEventListener('input',()=>{page=1;load()})
  // sortable headers
  document.querySelectorAll('#med-table thead th[data-sort]').forEach(th=>{
    th.style.cursor='pointer'
    th.addEventListener('click', ()=>{
      const s = th.getAttribute('data-sort')
      if(sort === s) order = (order === 'asc') ? 'desc' : 'asc'
      else { sort = s; order = 'asc' }
      page = 1; load()
    })
  })
  loadSummary()
  load()
}

// Medicine detail
if(typeof MED_ID !== 'undefined'){
  const token=localStorage.getItem('token')
  async function loadMed(){
    const r=await fetch('/api/medicines/'+MED_ID,{headers:{'Authorization':'Bearer '+token}})
    if(r.status===401){window.location='/login';return}
    const m=await r.json();
    document.getElementById('med-name').textContent = m.name
    document.getElementById('med-info').textContent = `Generic: ${m.generic_name||''} • Manufacturer: ${m.manufacturer||''} • Sellable: ${m.sellable_stock}`
    const tbody=document.querySelector('#batch-table tbody');tbody.innerHTML=''
     m.batches.forEach(b=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${b.batch_number}</td><td>${b.quantity}</td><td>${b.in_date||''}</td><td>${b.expiry_date}</td><td>${b.status}</td>`;tbody.appendChild(tr)})
  }
  document.getElementById('add-batch').addEventListener('submit',async e=>{
    e.preventDefault();const fd=new FormData(e.target);const body={batch_number:fd.get('batch_number'),quantity:fd.get('quantity'),in_date:fd.get('in_date'),expiry_date:fd.get('expiry_date')};
     const r=await postJSON('/api/medicines/'+MED_ID+'/batches', body);
     if(r.status===201){loadMed(); if(r.body && r.body.warning) alert(r.body.warning)}else alert(r.body.msg||'error')
  })
  
  document.getElementById('dispense-form').addEventListener('submit',async e=>{
    e.preventDefault();const fd=new FormData(e.target);const body={quantity:fd.get('quantity')};const res=await postJSON('/api/medicines/'+MED_ID+'/dispense', body);
    if(res.status===200||res.status===201){document.getElementById('dispense-result').textContent = JSON.stringify(res.body, null, 2); loadMed()} else alert(res.body.msg||'error')
  })
  loadMed()
}

// Alerts
if(document.getElementById('alerts-table')){
  document.getElementById('load').addEventListener('click', async ()=>{
    const token=localStorage.getItem('token'); const days=document.getElementById('days').value||30
    const r=await fetch('/api/alerts/expiry?days='+days,{headers:{'Authorization':'Bearer '+token}})
    const data=await r.json(); const tbody=document.querySelector('#alerts-table tbody');tbody.innerHTML=''
    data.forEach(a=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${a.medicine}</td><td>${a.batch_number}</td><td>${a.quantity}</td><td>${a.expiry_date}</td><td>${a.days_remaining}</td>`;tbody.appendChild(tr)})
  })
}
