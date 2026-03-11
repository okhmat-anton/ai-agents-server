import httpx
import json
async def execute(agent_name=None, question=None):
    from app.database import get_mongodb
    from app.mongodb.services import AgentService, AgentModelService, ModelConfigService
    from app.api.agent_files import read_agent_config
    from app.config import get_settings
    db = get_mongodb()
    svc = AgentService(db)
    # List mode: return all agents with expert questions
    if not agent_name or not question:
        agents = await svc.get_all(filter={'enabled': True}, limit=200)
        result = []
        for a in agents:
            config = read_agent_config(a.name)
            desc = config.get('description', a.description or '') if config else (a.description or '')
            mission = config.get('mission', '') if config else ''
            result.append({
                'name': a.name,
                'description': desc,
                'mission': mission,
                'expert_questions': a.expert_questions or [],
            })
        return {'agents': result, 'total': len(result)}
    # Ask mode: consult a specific agent
    agents = await svc.get_all(filter={'name': agent_name}, limit=1)
    if not agents:
        return {'error': f"Agent '{agent_name}' not found"}
    agent = agents[0]
    config = read_agent_config(agent.name)
    sys_prompt = config.get('system_prompt', agent.system_prompt) if config else agent.system_prompt
    mission = config.get('mission', '') if config else ''
    desc = config.get('description', agent.description or '') if config else (agent.description or '')
    eq = agent.expert_questions or []
    ctx = f'You are {agent.name}'
    if desc:
        ctx += f' — {desc}'
    ctx += '.\n'
    if mission:
        ctx += f'Your core mission: {mission}\n'
    if sys_prompt:
        ctx += f'\n{sys_prompt}\n'
    if eq:
        ctx += '\nYour areas of expertise:\n'
        for q in eq:
            ctx += f'- {q}\n'
    ctx += '\nAnother agent is consulting you. Answer based on your expertise, principles, and knowledge. Be concise and actionable.'
    # Resolve model for this agent
    settings = get_settings()
    am_svc = AgentModelService(db)
    agent_models = await am_svc.get_by_agent(agent.id)
    model_id = None
    if agent_models:
        mc_svc = ModelConfigService(db)
        for am in sorted(agent_models, key=lambda x: x.priority):
            mid = am.model_config_id
            if mid.startswith('role:'):
                role = mid[5:]
                mc = await mc_svc.find_one({'role': role})
                if mc:
                    model_id = mc.model_id
                    break
            else:
                mc = await mc_svc.get_by_id(mid)
                if mc:
                    model_id = mc.model_id
                    break
    if not model_id:
        model_id = 'llama3.1:8b'
    # Call Ollama
    ollama_url = settings.OLLAMA_BASE_URL
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f'{ollama_url}/api/chat',
            json={'model': model_id, 'messages': [
                {'role': 'system', 'content': ctx},
                {'role': 'user', 'content': question},
            ], 'stream': False},
        )
        if resp.status_code != 200:
            return {'error': f'LLM error {resp.status_code}: {resp.text[:500]}'}
        data = resp.json()
        answer = data.get('message', {}).get('content', '')
    return {'agent': agent.name, 'question': question, 'answer': answer, 'expert_questions': eq}
