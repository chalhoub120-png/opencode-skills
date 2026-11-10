INSERT INTO users (id, username, email, password_hash, api_key, role, language_preference, is_active)
VALUES
    ('715ae2b7-2591-45ac-96a9-b1dc37423055', 'demo', 'demo@local.ai', 'dummy', 'demo-key-001', 'user', 'ar', true),
    ('8e3f1a2b-3c4d-5e6f-7a8b-9c0d1e2f3a4b', 'admin', 'admin@local.ai', 'dummy', 'admin-key-001', 'admin', 'ar', true)
ON CONFLICT (api_key) DO NOTHING;

INSERT INTO agents (id, name, agent_type, system_prompt_ar, system_prompt_en, model_preference, temperature)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'CEO', 'ceo', 'أنت مدير تنفيذي تنسيق المهام الاستراتيجية.', 'You are a CEO orchestrating strategic tasks.', 'qwen3:32b', 0.3),
    ('22222222-2222-2222-2222-222222222222', 'Developer', 'developer', 'أنت مبرمج تكتب وتراجع الكود.', 'You are a developer writing and reviewing code.', 'qwen3:32b', 0.3),
    ('33333333-3333-3333-3333-333333333333', 'Researcher', 'researcher', 'أنت باحث تبحث وتلخص المعلومات.', 'You are a researcher searching and summarizing.', 'qwen3:32b', 0.3),
    ('44444444-4444-4444-4444-444444444444', 'Analyst', 'analyst', 'أنت محلل تحلل البيانات وتقرر.', 'You are an analyst analyzing data and deciding.', 'deepseek-r1:32b', 0.3),
    ('55555555-5555-5555-5555-555555555555', 'Security', 'security', 'أنت خبير أمن تدقق الثغرات.', 'You are a security expert auditing vulnerabilities.', 'deepseek-r1:32b', 0.3),
    ('66666666-6666-6666-6666-666666666666', 'Legal', 'legal', 'أنت مستشار قانوني تراجع العقود.', 'You are a legal counsel reviewing contracts.', 'deepseek-r1:32b', 0.3)
ON CONFLICT (name) DO NOTHING;
