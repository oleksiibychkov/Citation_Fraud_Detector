# Citation Fraud Detector (CFD) — TODO v1.6

> Відповідає Технічному завданню v1.6 (14 розділів, 1003 параграфи)
> Deployment: GitHub + Supabase + Render.com
> Локалізація: UA (основна) + EN

---

## Етап 1: MVP (Тижні 1–4)

> ТЗ §1–§3: Загальні відомості, Архітектура, Збір даних

### 1.1 Структура проекту
- [ ] Створити базову структуру проекту (каталоги, pyproject.toml, requirements.txt)
- [ ] Конфігурація .env: SCOPUS_API_KEY, SUPABASE_URL, SUPABASE_KEY, NEO4J_URI, NEO4J_PASSWORD
- [ ] GitHub repo + CI/CD: lint (ruff) → pytest → build (§13.6)
- [ ] Локалізація: ua.json, en.json базова структура (§13.5)

### 1.2 Модуль збору даних (§3)
- [ ] Вхідні параметри: прізвище + Scopus Author ID або ORCID (§3.3)
- [ ] Batch-режим: CSV-імпорт (surname, scopus_id, orcid) з дедуплікацією за ID (§3.3)
- [ ] Реалізувати абстрактний клас `DataSourceStrategy` (§3.2)
- [ ] Реалізувати `OpenAlexStrategy` (ендпоінти /works, /authors)
- [ ] Реалізувати `ScopusStrategy` (з валідацією API-ключа)
- [ ] Реалізувати `FallbackStrategy` (автоматичне переключення при помилках)
- [ ] CLI: `--author "Surname"`, `--scopus-id`, `--orcid`, `--source openalex|scopus`, `--lang ua|en`
- [ ] Rate limiting та retry з exponential backoff (§3.5)
- [ ] Збір усіх полів метаданих (включаючи cited_by_timestamp!) (§3.4)

### 1.3 Edge Cases (§3.5)
- [ ] Автора не знайдено → повідомлення; batch — пропуск із фіксацією
- [ ] Автор < N_min публікацій → статус "Insufficient data" (§3.6)
- [ ] API неповні дані (немає cited_by_timestamp) → аналіз з попередженням, темпоральні = N/A
- [ ] Прізвище не збігається з API → попередження "Підтвердіть?"
- [ ] ORCID та Scopus ID → різні люди → блокування аналізу
- [ ] Автор змінив прізвище → зберігати всі варіанти від API
- [ ] API rate limit → exponential backoff; batch — пауза та продовження
- [ ] Дублікати у CSV → дедуплікація за ID з попередженням

### 1.4 Мінімальні вимоги для аналізу (§3.6)
- [ ] Порогові значення (налаштовувані): публікацій ≥10, цитувань ≥20, h-index ≥3
- [ ] Якщо не досягнуто → статус "Insufficient data" замість Fraud Score

### 1.5 Кеш-шар (Рівень 1) та аналітична БД
- [ ] Supabase PostgreSQL: таблиці authors, publications, citations, indicators, fraud_scores (§4)
- [ ] Кеш API: hash(endpoint + params), TTL 7 днів, інвалідація
- [ ] Збереження завантажених даних у аналітичну БД
- [ ] Unit-тести для DataSource модуля

### 1.6 Побудова графа (базова) (§5)
- [ ] Побудова орієнтованого графа G=(V,E) з NetworkX
- [ ] Розрахунок Degree Centrality (in-degree, out-degree)
- [ ] Розрахунок Self-Citation Ratio: SCR = |self_cit(a)| / |cit(a)|
- [ ] Розрахунок MCR(a,b) = 2|cit(a→b) ∩ cit(b→a)| / (|cit(a)| + |cit(b)|) (§6, Означення 6.7)
- [ ] Збереження результатів у таблицю indicators
- [ ] Unit-тести для графових метрик

### 1.7 CLI та базовий експорт
- [ ] Вивід результатів у консоль (таблиця з метриками)
- [ ] Інкрементальне оновлення: перевірка "що змінилося" при повторному аналізі
- [ ] Експорт у JSON
- [ ] README.md з інструкцією по запуску

---

## Етап 2: Графовий аналіз + Neo4j + Математичне обґрунтування (Тижні 5–8)

> ТЗ §5: Графовий аналіз, §6: Математичне обґрунтування детекції

### 2.1 Neo4j інтеграція (Рівень 3 — Граф) (§5)
- [ ] Розгортання Neo4j Docker на Render.com (§13.6)
- [ ] Модель графу: вузли Author, Publication; ребра AUTHORED, CITES, PUBLISHED_IN, AFFILIATED_WITH
- [ ] ETL-процес: Supabase PostgreSQL → Neo4j (автоматична синхронізація)
- [ ] Cypher-запити для citation rings: MATCH (a)-[:CITES]->(b)-[:CITES]->(c)-[:CITES]->(a)
- [ ] Cypher-запити для mutual citations: MATCH (a)-[:CITES]->(b), (b)-[:CITES]->(a)
- [ ] Neo4j GDS: Louvain community detection (§5.3)
- [ ] Neo4j GDS: PageRank, Betweenness Centrality (§5.2)
- [ ] Збереження результатів назад у Supabase

### 2.2 Розширені метрики центральності (§5.2)
- [ ] Eigenvector Centrality
- [ ] Betweenness Centrality
- [ ] PageRank (адаптований для зваженого графа)
- [ ] Unit-тести для розширених метрик

### 2.3 Community Detection (§5.3)
- [ ] Алгоритм Лувена через Neo4j GDS
- [ ] Порівняння внутрішньої vs. зовнішньої щільності кластерів
- [ ] Modularity score
- [ ] Позначення ізольованих кластерів як підозрілих

### 2.4 Виявлення клік (§5.4)
- [ ] Пошук cliques розміром k ≥ 3 через Neo4j
- [ ] Ранжування клік за розміром та щільністю цитувань
- [ ] Позначення клік за Теоремою 3 (§6.4): k≤4 — Low/Moderate; k=5 — Moderate (p<0.005); k=6 — High (p<10⁻⁸); k≥7 — Critical (p<10⁻¹⁴)

### 2.5 Реалізація математичної ієрархії детекції (§6)
- [ ] **Теорема 1 (§6.2):** Фільтр ациклічності G_auth[S] — виключення "чистих" груп
- [ ] **Теорема 2 (§6.3):** Обчислення μ(S) для підмножини авторів; порівняння з discipline baseline μ_D ± σ_D; нерівність Кантеллі P ≤ 1/(1+z²) = 0.10 при z=3
- [ ] **Теорема 3 (§6.4):** Пошук k-клік у G_mutual; обчислення P(∃K_k) ≤ C(n,k)×p^(k(k-1)/2)
- [ ] Алгоритм ієрархії (§6.5): Т1(фільтр) → Т2(статистика) → Т3(структура)
- [ ] Побудова G_mutual з порогом MCR > τ = 0.3 (Означення 6.8)
- [ ] Discipline baseline: емпіричне обчислення μ_D та σ_D (Означення 6.10)

### 2.6 Додаткові структурні індикатори (§7.1)
- [ ] Citation Bottleneck: CB = max_k(cit_k→a) / |cit(→a)|, поріг >0.30
- [ ] Reference List Anomaly (RLA) — аналіз списків літератури
- [ ] Geographic/Institutional Clustering (GIC): ентропія Шеннона H = −Σp_i log₂ p_i
- [ ] Unit-тести для кожного індикатора

### 2.7 Масштабованість (§5.5)
- [ ] Автоматичне переключення NetworkX → igraph при >50K вузлів
- [ ] Neo4j як основний графовий движок для всіх масштабів
- [ ] Бенчмарки продуктивності

---

## Етап 3: Темпоральний аналіз (Тижні 9–12)

> ТЗ §7: Детекція аномалій (темпоральні індикатори), §4: Модель даних

### 3.1 Повна схема Supabase PostgreSQL (§4)
- [ ] Усі 15 таблиць згідно ТЗ: authors, publications, citations, indicators, fraud_scores, snapshots, watchlist, peer_groups, discipline_baselines, embeddings, author_connections, report_evidence, algorithm_versions, audit_log + кеш
- [ ] pgvector для sentence embeddings
- [ ] Alembic для версіонування міграцій (§4.4)
- [ ] RLS (Row Level Security) через Supabase Auth (§13.6)
- [ ] Seed-дані для discipline_baselines (≥5 дисциплін)

### 3.2 h-Index Temporal Analysis (§7.1)
- [ ] Розрахунок h(t) — h-індекс як функція часу
- [ ] Growth Rate: середньорічний темп зростання за 5–10 років
- [ ] Виявлення аномалій dh/dt без відповідного збільшення публікацій
- [ ] h(t) vs. N(t) кореляційний аналіз

### 3.3 Temporal Anomaly Detection (§7.1)
- [ ] Z-score аналіз місячних/річних спайків цитувань
- [ ] Налаштовуваний поріг чутливості (за замовчуванням 3σ)
- [ ] Перехресна перевірка з кількістю нових публікацій

### 3.4 Price's Law та Citation Velocity (§7.1)
- [ ] Модель очікуваного старіння цитувань
- [ ] CV(paper) = citations_in_first_N_months / expected_for_journal_tier
- [ ] Нормалізація за квартилями журналу (Q1–Q4)
- [ ] Поріг: CV > 5× від медіани для журналу

### 3.5 Sleeping Beauty Detector (§7.1)
- [ ] Beauty Coefficient (B): кількісна міра "сну" та "пробудження"
- [ ] Дискримінація: легітимне пробудження (hot topic) vs. штучне (citation ring)
- [ ] Перехресна перевірка з Temporal Anomaly та Citation Bottleneck

### 3.6 Контекстуальний аналіз аномалій (§7.2)
- [ ] Детектор легітимних причин стрибків (breakthrough effect, hot topic, зміна афіліації, review-статті, нагороди)
- [ ] Алгоритм 4-крокової контекстуальної перевірки: тригер → контекст → структура → агрегація
- [ ] Правило "≥3 незалежних індикатори" для підвищення Fraud Score
- [ ] Перевірка пропорційності зростання переглядів vs. цитувань

### 3.7 Discipline Baseline та Journal-Level Analysis (§7.1)
- [ ] Збір середніх показників для ≥5 наукових дисциплін
- [ ] Нормалізація індикаторів відносно discipline baseline
- [ ] Journal self-citation rate
- [ ] Виявлення coercive citation practices

---

## Етап 4: Візуалізація, звітність та Dashboard (Тижні 13–16)

> ТЗ §8: Рівні впевненості, §9: Візуалізація та звітність, §10–§11: Roadmap та Dashboard

### 4.1 Система рівнів впевненості (§8)
- [ ] 5-рівнева шкала: Normal (0.0–0.2), Low (0.2–0.4), Moderate (0.4–0.6), High (0.6–0.8), Critical (0.8–1.0)
- [ ] Зважена агрегація Fraud Score = Σ(w_i × indicator_i) / Σ(w_i) (§8.2)
- [ ] Кольорове кодування у звітах та візуалізаціях
- [ ] Кожен звіт містить algorithm_version (§13.8)

### 4.2 Інтерактивна візуалізація (§9)
- [ ] Plotly: інтерактивний граф цитатної мережі (кольори → confidence level, розмір → citation_count)
- [ ] h(t) vs. N(t) графіки
- [ ] Heatmap взаємного цитування (матриця інтенсивності)
- [ ] Temporal spike charts з позначеними аномаліями
- [ ] Discipline baseline overlay

### 4.3 Модуль звітності (§9)
- [ ] **Анти-рейтинг PDF**: ранжований список авторів за Fraud Score (§9.1)
- [ ] **Evidence Store**: сховище доказів із прив'язкою до звітів (§9.2, таблиця report_evidence)
- [ ] **Connection Map**: візуалізація зв'язків автора (§9.3, таблиця author_connections)
- [ ] **Author Dossier**: повне досьє з усіма метриками та історією (§9.4)
- [ ] Формати експорту: JSON, CSV, PDF (ReportLab), HTML з Plotly
- [ ] Структура звіту: 7 секцій згідно ТЗ
- [ ] Локалізація звітів: --lang ua|en (§13.5)

### 4.4 Dashboard та Watch-list (§11)
- [ ] Dashboard frontend: React або Svelte на Render.com / GitHub Pages (§13.6)
- [ ] Перемикач мови UA/EN (§13.5)
- [ ] Watch-list: додавання автора за Scopus ID або ORCID
- [ ] Налаштування порогів чутливості для кожного автора
- [ ] Періодичний перезбір: GitHub Actions cron щотижня (§13.6)
- [ ] Порівняння з попереднім snapshot
- [ ] Нотифікації при зміні Fraud Score ≥0.1 (email, webhook)
- [ ] Історія змін метрик (snapshots timeline)
- [ ] Зведена таблиця з кольоровим кодуванням
- [ ] Фільтрація за рівнем впевненості, дисципліною, датою
- [ ] Попередження при порівнянні результатів різних algorithm_version (§13.8)

---

## Етап 5: Розширена аналітика (Тижні 17–20)

> ТЗ §7: Додаткові індикатори, §10: Розширені модулі

### 5.1 Authorship Network Anomaly (ANA) (§7.1)
- [ ] Виявлення гостьового/гіфтового авторства
- [ ] Кластеризація за реальною участю

### 5.2 Peer Benchmark (PB) (§7.1)
- [ ] Алгоритм підбору двійників за k-NN (discipline, career_start_year, publication_count)
- [ ] Збереження peer groups у таблиці peer_groups
- [ ] Порівняння h(t), SCR, MCR, CV з медіаною peer group
- [ ] Z-score відхилення від peer group для кожного індикатора

### 5.3 Salami Slicing Detector (SSD) (§7.1)
- [ ] Sentence embeddings (pgvector) для порівняння абстрактів
- [ ] Cosine similarity threshold >0.7 для пар статей одного автора
- [ ] Серії статей з мінімальним інтервалом (<30 днів) + подібні назви

### 5.4 Citation Cannibalism (CC) (§7.1)
- [ ] CC(paper) = self_citations_in_references / total_references
- [ ] Поріг CC > 0.50 для окремої статті
- [ ] Кореляція з SSD (висока подібність + високий CC = подвійний сигнал)

### 5.5 Cross-Platform Consistency Check (CPC) (§7.1)
- [ ] Порівняння publication_count, citation_count, h-index між OpenAlex та Scopus
- [ ] Поріг розходження >20% — попередження
- [ ] Fuzzy matching за DOI, назвою, авторами

### 5.6 Калібрування та якість (§14)
- [ ] Тестовий набір від замовника: відомі маніпуляції (Retraction Watch, PubPeer) + контрольна група (clean) + граничні випадки (breakthrough) (§13.7)
- [ ] Semi-supervised learning для калібрування ваг w_i
- [ ] Anchor point: Теорема 3 (k≥5) → Moderate
- [ ] Target: Precision ≥0.80, Recall ≥0.70, F1 ≥0.75, FPR ≤0.10 (§13.7)
- [ ] Аналіз false positive rate по дисциплінах

---

## Етап 6: Інтеграція, API та Deployment (Тижні 21–24)

> ТЗ §12: REST API, §13: NFR, §14: Критерії приймання

### 6.1 REST API (§12)
- [ ] FastAPI backend на Render.com (§13.6)
- [ ] OpenAPI/Swagger документація
- [ ] GET /api/v1/author/{id}/report — повний звіт
- [ ] GET /api/v1/author/{id}/score — Fraud Score
- [ ] GET /api/v1/author/{id}/indicators — деталізація
- [ ] GET /api/v1/author/{id}/graph — граф (JSON)
- [ ] POST /api/v1/batch/analyze — batch-аналіз (CSV)
- [ ] POST /api/v1/watchlist/add — додати до Watch-list
- [ ] GET /api/v1/watchlist — список з поточними оцінками
- [ ] GET /api/v1/watchlist/{id}/history — історія змін
- [ ] GET /api/v1/audit — журнал дій (admin only) (§13.9)
- [ ] Accept-Language header для локалізації відповідей (§13.5)
- [ ] API-ключі з ролями (reader, analyst, admin)
- [ ] Rate limiting за API-ключем

### 6.2 Версіонування індикаторів (§13.8)
- [ ] Таблиця algorithm_versions: id, version (semver), release_date, thresholds (JSONB), weights (JSONB), changelog
- [ ] Major: зміна індикаторів/логіки агрегації
- [ ] Minor: зміна порогів/ваг
- [ ] Patch: виправлення помилок
- [ ] Кожен fraud_score та indicator містить algorithm_version

### 6.3 Аудит-лог (§13.9)
- [ ] Таблиця audit_log (append-only, зберігання ≥3 роки)
- [ ] Поля: id, timestamp, user_id, action, target_author_id, details (JSONB), ip_address
- [ ] Actions: analyze, batch_analyze, generate_report, view_dossier, add_watchlist, export_data
- [ ] API endpoint: GET /api/v1/audit (admin only)

### 6.4 Інтеграція з CRIS-системами (§12.4)
- [ ] Pure (Elsevier): webhook при додаванні дослідника
- [ ] Converis (Clarivate): REST-інтеграція
- [ ] VIVO: SPARQL-ендпоінт
- [ ] OpenAPI-специфікація для кастомних інтеграцій

### 6.5 Deployment та CI/CD (§13.6)
- [ ] GitHub: код, CI/CD (Actions), Issues
- [ ] Supabase: PostgreSQL + pgvector + Auth + RLS
- [ ] Render.com: FastAPI backend + Neo4j Docker
- [ ] GitHub Pages або Render: Dashboard frontend
- [ ] CI/CD pipeline: push → lint (ruff) → pytest → build Docker → deploy
- [ ] PR → lint + tests + coverage report
- [ ] Scheduled: щотижневий Watch-list cron (GitHub Actions)
- [ ] Secrets: SCOPUS_API_KEY, SUPABASE_URL, SUPABASE_KEY, NEO4J_URI, NEO4J_PASSWORD

### 6.6 Тестування (§13.7)
- [ ] Unit-тести: покриття ≥80%
- [ ] Integration tests з мок-даними
- [ ] Тестовий набір від замовника (конкретні Scopus ID/ORCID)
- [ ] Security review API (автентифікація, rate limiting, injection protection)

### 6.7 Фіналізація
- [ ] Повна документація (Docstring + MkDocs)
- [ ] README з прикладами використання (UA + EN)
- [ ] CHANGELOG.md
- [ ] Локалізація UA/EN повна перевірка (§13.5)
- [ ] Етичні аспекти (§13.4): застереження в звітах, disclaimer "оцінка підозрілості, а не вирок"
- [ ] Резервне копіювання: pg_dump (Supabase), neo4j-admin dump (§4.5)

---

## Критерії приймання (§14)

### MVP (Етап 1)
- [ ] CLI аналіз автора за прізвищем + Scopus ID / ORCID
- [ ] ≥5 базових індикаторів (MCR, SCR, CB, TA, HTA)
- [ ] JSON-звіт з Fraud Score
- [ ] Обробка edge cases згідно §3.5

### Фінальний продукт
- [ ] 15 індикаторів, 5-рівнева шкала
- [ ] Математична ієрархія: Теорема 1 → 2 → 3 (§6)
- [ ] Dashboard + Watch-list
- [ ] REST API з документацією
- [ ] Локалізація UA/EN
- [ ] Версіонування: кожен звіт містить algorithm_version
- [ ] Аудит-лог: append-only, ≥3 роки
- [ ] Deployment: GitHub + Supabase + Render
- [ ] Precision ≥0.80, Recall ≥0.70, FPR ≤0.10 на тестовому наборі
