from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio, json, math, random

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])
risk = json.load(open('frontend/src/mocks/risk.json'))
cases = json.load(open('frontend/src/mocks/cases.json'))
scenarios = json.load(open('frontend/src/mocks/scenarios.json'))

@app.get('/health')
def health(): return {'ok': True, 'chain': True, 'detector': 'mock'}
@app.get('/scenarios')
def get_scenarios(): return scenarios
@app.get('/cases')
def get_cases(): return cases
@app.get('/risk/latest')
def latest(): return risk
@app.post('/run/start')
def start(body: dict): return {'run_id': 'demo-2026-09-18'}
@app.post('/case/{case_id}/challenge')
def challenge(case_id: int): return JSONResponse({'case_id': case_id, 'status': 'CHALLENGED', 'challenge_tx': '0xchallenge...demo'})

@app.websocket('/ws/live')
async def live(ws: WebSocket):
    await ws.accept()
    for t in range(600):
        progress = t / 599
        score = round(20 + progress * 70)
        price = 100 + math.sin(t / 18) * .4 + progress * 3.8
        await ws.send_json({'type':'tick','payload':{'run_id':'demo-2026-09-18','t':t,'event':'quote','agent_id':'A2' if t % 2 else 'A3','side':'ask','price':round(price,2),'quantity':5.0,'capital':50000.0,'pnl':round(820 + progress * 423,2),'pool':{'reserve_x':10420,'reserve_y':981100,'fee_bps':30},'oracle_price':round(100 + math.sin(t/28)*.15,2),'shock': 'oracle' if t in (180, 360) else None}})
        if t % 20 == 0:
            payload = {**risk, 'risk_score': score, 'verdict': 'HIGH' if score >= 70 else 'MEDIUM' if score >= 40 else 'LOW', 'counterfactual': {**risk['counterfactual'], 'observed_price': round(price,2)}}
            await ws.send_json({'type':'risk','payload':payload})
        await asyncio.sleep(.05)
