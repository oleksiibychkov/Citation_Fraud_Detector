"""Досьє автора — повний аналіз з 4 візуалізаціями."""

from __future__ import annotations

import streamlit as st

from cfd.visualization.colors import LEVEL_COLORS

VALID_LEVELS = {"normal", "low", "moderate", "high", "critical"}

# Опис індикаторів: код, повна назва, що вимірює
INDICATOR_INFO: dict[str, tuple[str, str]] = {
    "SCR": (
        "Коефіцієнт самоцитування",
        "Частка самоцитувань у загальній кількості цитувань. "
        "Високі значення вказують на надмірне цитування автором власних робіт.",
    ),
    "MCR": (
        "Коефіцієнт взаємного цитування",
        "Виявляє взаємні домовленості про цитування між авторами — "
        "патерн «я цитую тебе, ти цитуєш мене».",
    ),
    "CB": (
        "Цитатне «вузьке горло»",
        "Концентрація вхідних цитувань з одного джерела. "
        "Високе значення означає, що більшість цитувань надходить від одного автора/групи.",
    ),
    "TA": (
        "Темпоральна аномалія",
        "Виявляє неприродні сплески кількості цитувань, які не корелюють "
        "з публікаційною активністю (аналіз Z-оцінки).",
    ),
    "HTA": (
        "Темпоральний аналіз h-індексу",
        "Аналізує швидкість зростання h-індексу у часі. Позначає аномально швидке "
        "зростання, яке не пояснюється публікаційною активністю.",
    ),
    "RLA": (
        "Аномалія списку літератури",
        "Оцінює різноманітність списків літератури. Високі значення вказують на вузьке "
        "коло цитування — постійне посилання на одні й ті самі джерела.",
    ),
    "GIC": (
        "Географічна/інституційна кластеризація",
        "Вимірює концентрацію цитуючих авторів за інституцією/географією. "
        "Високі значення означають, що цитування надходять з дуже вузького кола.",
    ),
    "EIGEN": (
        "Власна векторна центральність",
        "Показник мережевого впливу — чи пов'язані роботи автора з іншими "
        "високоцитованими роботами, чи ізольовані в малому кластері?",
    ),
    "BETWEENNESS": (
        "Центральність за посередництвом",
        "Наскільки часто роботи автора є «мостами» у цитатній мережі. "
        "Аномальні значення можуть вказувати на штучне позиціонування в мережі.",
    ),
    "PAGERANK": (
        "Центральність PageRank",
        "Оцінка важливості в цитатній мережі за алгоритмом Google. "
        "Аномальний PageRank може свідчити про маніпуляції з цитуваннями.",
    ),
    "COMMUNITY": (
        "Виявлення спільнот",
        "Алгоритм Лувена виявляє щільні цитатні кластери. "
        "Позначає підозрілі спільноти з високою внутрішньою, але низькою зовнішньою щільністю цитувань.",
    ),
    "CLIQUE": (
        "Виявлення цитатних клік",
        "Виявляє тісно пов'язані групи, де всі цитують усіх — "
        "класична ознака організованих маніпуляцій з цитуваннями.",
    ),
    "CV": (
        "Швидкість цитування",
        "Вимірює, наскільки швидко статті накопичують цитування відносно їхнього віку, "
        "дисципліни та журналу. Аномально швидке накопичення є підозрілим.",
    ),
    "SBD": (
        "Детектор «сплячих красунь»",
        "Ідентифікує статті, які «спали» роками, а потім раптово отримали багато цитувань — "
        "можлива ознака координованих цитатних кампаній.",
    ),
    "ANA": (
        "Аномалія мережі авторства",
        "Виявляє патерни «гостьового» авторства: багато одноразових співавторів, "
        "незвичайні позиції автора, низький рівень повторної співпраці.",
    ),
    "CC": (
        "Цитатний канібалізм",
        "Надмірне самоцитування у списках літератури статей — "
        "автор постійно посилається на власні роботи в кожній новій статті.",
    ),
    "SSD": (
        "Детектор «нарізки салямі»",
        "Виявляє подрібнення публікацій — публікація дуже схожих статей за короткий час "
        "для штучного збільшення кількості публікацій.",
    ),
    "PB": (
        "Порівняння з колегами",
        "Порівнює метрики автора (h-індекс, цитування, публікації) з аналогічними колегами. "
        "Великі відхилення можуть вказувати на штучне завищення показників.",
    ),
    "CPC": (
        "Крос-платформна узгодженість",
        "Порівнює метрики між OpenAlex та Scopus. "
        "Велика розбіжність (>20%) може свідчити про маніпуляції з даними або проблеми профілю.",
    ),
    "JSCR": (
        "Рівень самоцитування журналу",
        "Частка посилань, що вказують на той самий журнал. "
        "Високі значення можуть свідчити про маніпуляції на рівні журналу.",
    ),
    "COERCE": (
        "Виявлення примусового цитування",
        "Виявляє ознаки примусу з боку журналів до цитування власних публікацій — "
        "висока концентрація, зміщення до нещодавніх робіт та зростаючий тренд.",
    ),
    "CTX": (
        "Контекстний аналіз аномалій",
        "Мета-індикатор, що агрегує множинні сигнали та перевіряє наявність легітимних "
        "пояснень (оглядові статті, актуальні теми). Фінальний етап верифікації.",
    ),
}

LEVEL_CONCLUSIONS = {
    "normal": (
        "Ознак маніпуляцій з цитуваннями не виявлено. "
        "Цитатний профіль автора відповідає нормальній академічній діяльності. "
        "Усі індикатори знаходяться в межах очікуваних значень для дисципліни та етапу кар'єри."
    ),
    "low": (
        "Виявлено незначні відхилення від типових цитатних патернів. "
        "Це можуть бути природні варіації або ранні попереджувальні сигнали. "
        "Безпосередньої загрози немає, але рекомендується періодичний моніторинг."
    ),
    "moderate": (
        "Кілька індикаторів показують відхилення від очікуваних цитатних патернів. "
        "Це не є доказом маніпуляцій, але потребує більш детального вивчення. "
        "Рекомендація: перегляньте спрацьовані індикатори та порівняйте з нормами дисципліни."
    ),
    "high": (
        "Виявлено значні аномалії за кількома цитатними індикаторами. "
        "Патерн узгоджується з можливими практиками маніпулювання цитуваннями. "
        "Рекомендація: детальний ручний аналіз експертною комісією, "
        "перехресна перевірка з даними Scopus та вивчення конкретних спрацьованих індикаторів."
    ),
    "critical": (
        "Виявлено переконливі ознаки систематичних цитатних аномалій. "
        "Кілька незалежних індикаторів вказують на патерни маніпуляцій: "
        "цитатні кільця, надмірне самоцитування, темпоральні сплески та/або примусові практики. "
        "Рекомендація: негайний експертний огляд, інституційне розслідування "
        "та порівняння з верифікованими даними Scopus/Web of Science."
    ),
}

LEVEL_LABELS = {
    "normal": "НОРМА",
    "low": "НИЗЬКИЙ РИЗИК",
    "moderate": "ПОМІРНИЙ РИЗИК",
    "high": "ВИСОКИЙ РИЗИК",
    "critical": "КРИТИЧНИЙ РИЗИК",
}


def render():
    """Render the author dossier page."""
    st.header("Досьє автора")

    # Форма введення
    col1, col2, col3 = st.columns(3)
    with col1:
        author_name = st.text_input("Прізвище автора")
    with col2:
        scopus_id = st.text_input("Scopus ID")
    with col3:
        orcid = st.text_input("ORCID")

    # Scopus доступний лише з ключем
    from cfd.config.settings import Settings as _Settings

    _s = _Settings()
    sources = ["openalex", "auto"]
    if _s.scopus_api_key:
        sources.append("scopus")
    source = st.selectbox("Джерело даних", sources)

    if not st.button("Аналізувати"):
        return

    if not author_name:
        st.error("Прізвище автора є обов'язковим.")
        return

    if not scopus_id and not orcid:
        st.error("Потрібно вказати Scopus ID або ORCID.")
        return

    # Запуск аналізу
    with st.spinner("Аналізуємо..."):
        result, author_data = _run_analysis(author_name, scopus_id, orcid, source)

    if result is None:
        st.error("Аналіз не вдався. Перевірте вхідні дані та спробуйте знову.")
        return

    # Дисклеймер джерела даних
    api_used = getattr(result.author_profile, "source_api", source) or source
    if api_used == "openalex":
        st.info(
            "Джерело даних: **OpenAlex** (безкоштовне). "
            "OpenAlex може мати неповне покриття порівняно зі Scopus — "
            "h-індекс, кількість публікацій та цитувань можуть бути нижчими. "
            "Для точніших даних налаштуйте ключ Scopus API (`CFD_SCOPUS_API_KEY`)."
        )

    # Розділ 1: Профіль автора
    st.subheader("Профіль автора")
    profile = result.author_profile
    info_cols = st.columns(4)
    info_cols[0].metric("Ім'я", profile.full_name or author_name)
    info_cols[1].metric("h-індекс", profile.h_index if profile.h_index is not None else "\u2014")
    info_cols[2].metric("Публікацій", profile.publication_count if profile.publication_count is not None else "\u2014")
    info_cols[3].metric("Цитувань", profile.citation_count if profile.citation_count is not None else "\u2014")

    # Розділ 2: Оцінка шахрайства
    st.subheader("Оцінка шахрайства")
    level = result.confidence_level or "normal"
    if level not in VALID_LEVELS:
        level = "normal"
    color = LEVEL_COLORS.get(level, "#999999")
    level_ua = LEVEL_LABELS.get(level, level.upper())
    st.markdown(
        f"<h2 style='color:{color}'>{result.fraud_score:.4f} \u2014 {level_ua}</h2>",
        unsafe_allow_html=True,
    )

    # Розділ 3: Індикатори з описами
    st.subheader("Індикатори")
    triggered = set(result.triggered_indicators)
    triggered_details = []
    normal_details = []

    for ind in result.indicators:
        name = ind.indicator_type
        value = ind.value
        is_triggered = name in triggered
        info = INDICATOR_INFO.get(name)
        full_name = info[0] if info else name
        description = info[1] if info else ""

        if is_triggered:
            triggered_details.append((name, full_name, value, description))
        else:
            normal_details.append((name, full_name, value, description))

    # Спрацьовані (підозрілі) індикатори — першими
    if triggered_details:
        st.markdown("#### \u26a0\ufe0f Спрацьовані індикатори (перевищено поріг)")
        for code, full_name, value, description in triggered_details:
            with st.expander(f"\u26a0\ufe0f **{code}** ({full_name}): {value:.4f}", expanded=True):
                st.markdown(description)

    # Нормальні індикатори (згорнуті)
    if normal_details:
        st.markdown("#### \u2705 Нормальні індикатори (в межах порогу)")
        for code, full_name, value, description in normal_details:
            with st.expander(f"\u2705 **{code}** ({full_name}): {value:.4f}"):
                st.markdown(description)

    # Розділ 4: Попередження
    if result.warnings:
        st.subheader("Попередження")
        for w in result.warnings:
            st.warning(w)

    # Розділ 5: Візуалізації
    st.subheader("Візуалізації")
    _render_visualizations(author_data, result)

    # Розділ 6: Висновок
    _render_conclusion(result, level, color)


def _render_conclusion(result, level, color):
    """Render a detailed conclusion about the analysis."""
    st.subheader("Висновок")

    triggered = result.triggered_indicators
    total = len(result.indicators)
    triggered_count = len(triggered)
    score = result.fraud_score

    # Підсумкові метрики
    col1, col2, col3 = st.columns(3)
    col1.metric("Проаналізовано індикаторів", total)
    col2.metric("Спрацювало індикаторів", triggered_count)
    col3.metric("Оцінка шахрайства", f"{score:.4f}")

    # Вердикт
    verdict = LEVEL_LABELS.get(level, level.upper())

    st.markdown(
        f"### Вердикт: <span style='color:{color}'>{verdict}</span>",
        unsafe_allow_html=True,
    )

    # Розгорнутий висновок
    conclusion = LEVEL_CONCLUSIONS.get(level, "")
    st.markdown(conclusion)

    # Перелік спрацьованих індикаторів
    if triggered:
        st.markdown("**Спрацьовані індикатори:**")
        for code in triggered:
            info = INDICATOR_INFO.get(code)
            full_name = info[0] if info else code
            value = 0.0
            for ind in result.indicators:
                if ind.indicator_type == code:
                    value = ind.value
                    break
            st.markdown(f"- **{code}** ({full_name}): {value:.4f}")

    # Дисклеймер
    from cfd.dashboard.disclaimer import render_disclaimer

    render_disclaimer()


def _run_analysis(author_name, scopus_id, orcid, source):
    """Run the analysis pipeline."""
    try:
        from cfd.cli.main import _build_pipeline, _build_strategy
        from cfd.config.settings import Settings

        settings = Settings()
        strategy = _build_strategy(source, settings)
        pipeline = _build_pipeline(strategy, settings)

        result = pipeline.analyze(author_name, scopus_id=scopus_id or None, orcid=orcid or None)

        # Збір даних для візуалізацій
        try:
            author_data = strategy.collect(author_name, scopus_id=scopus_id or None, orcid=orcid or None)
        except Exception:
            from cfd.data.models import AuthorData

            author_data = AuthorData(profile=result.author_profile, publications=[], citations=[])

        return result, author_data
    except Exception as e:
        st.error(f"Помилка: {e}")
        return None, None


def _render_visualizations(author_data, result):
    """Render all 4 visualization types."""
    tab1, tab2, tab3, tab4 = st.tabs([
        "Цитатна мережа",
        "Часовий ряд h(t)/N(t)",
        "Теплова карта взаємоцитувань",
        "Графік сплесків",
    ])

    try:
        from cfd.visualization.heatmap import build_mutual_heatmap
        from cfd.visualization.network import build_network_figure
        from cfd.visualization.temporal import build_ht_nt_figure, build_spike_chart

        with tab1:
            fig = build_network_figure(author_data, result)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            fig = build_ht_nt_figure(author_data)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            fig = build_mutual_heatmap(author_data)
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            fig = build_spike_chart(author_data, result)
            st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        st.warning("Для візуалізацій потрібен Plotly. Встановіть: pip install citation-fraud-detector[viz]")
    except Exception as e:
        st.warning(f"Не вдалося побудувати візуалізації: {e}")
