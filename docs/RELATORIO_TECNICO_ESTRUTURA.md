# Estrutura Base para o Relatório Técnico Acadêmico (Até 10 Páginas) e Roteiro de Apresentação
**Disciplina:** Projeto Integrador V – B | **Curso:** Big Data e Inteligência Artificial — PUC Goiás  
**Organização Parceira:** Integra Engenharia de Sistemas  

---

## Parte 1 — Estrutura Sugerida para o Relatório Técnico (Máx. 10 Páginas)

### 1. Caracterização da Organização (1 página)
- Apresentação da **Integra Engenharia de Sistemas** e seu portfólio de soluções em softwares de gestão empresarial (ERP).
- Atividades centrais: desenvolvimento e manutenção de sistemas, implantação, suporte técnico, treinamento de usuários e implementação de novas funcionalidades.
- Conexão com o projeto anterior (dashboard interno de SLA, Lead Time e produtividade sobre banco Firebird) e justificativa da expansão para inteligência de mercado com dados externos de mídias sociais.

### 2. Problema Investigado e Objetivos (1 página)
- Definição do problema de pesquisa: compreender como consumidores e usuários corporativos discutem sistemas ERP, implantação, suporte técnico e automação em plataformas públicas (YouTube, Instagram e Reddit).
- Delimitação ética e metodológica: esclarecimento explícito de que os dados constituem uma amostra exploratória do mercado geral de software de gestão, sem atribuir comentários de terceiros à Integra Engenharia de Sistemas.

### 3. Metodologia (1,5 páginas)
- Pesquisa aplicada e exploratória com pipeline de Engenharia de Dados e Big Data.
- Coleta baseada em 6 palavras-chave de domínio (`Sistema ERP`, `Software de gestão empresarial`, `Implantação de ERP`, `Suporte técnico de sistemas`, `Dificuldades com ERP`, `Automação empresarial`).
- **Classificação Heurística Exploratória:** explicação transparente do léxico de sentimentos (`Positivo`, `Negativo`, `Neutro`) e das 7 categorias temáticas (`Atendimento e suporte`, `Implantação`, `Preço e custo`, `Funcionalidades`, `Desempenho e lentidão`, `Integração e automação`, `Outros`).
- Conformidade com a LGPD: coleta restrita a dados públicos via Actors oficiais do Apify, pseudonimização de menções (`@[USUARIO]`) e exclusão de datasets do repositório Git.

### 4. Arquitetura da Solução (1,5 páginas)
- Fluxo ponta a ponta: `YouTube + Instagram + Reddit → Apify → Python → Pandas → Hadoop/HDFS → Apache Hive → Streamlit/Plotly`.
- Desacoplamento de configurações em `config/actors/*.json` e variáveis de ambiente (`.env`).
- Tolerância a falhas na coleta (isolamento de erros por plataforma e retentativas com backoff progressivo).

### 5. Coleta, Tratamento e Armazenamento no HDFS (1,5 páginas)
- Detalhamento dos Actors verificados:
  - YouTube: `streamers/youtube-scraper`
  - Instagram: `apify/instagram-scraper`
  - Reddit: `trudax/reddit-scraper-lite`
- Regras de normalização no Pandas (`processamento/normalizar_dados.py`): modelo unificado de 20 colunas, preservação de nulos para métricas não equivalentes, datas em ISO 8601 e remoção de duplicidades por `(plataforma, tipo_registro, id_registro)`.
- Estrutura de diretórios no HDFS (`/projeto_integrador/dados_brutos/...` e `/projeto_integrador/dados_tratados/multiplataforma/`) gerenciada por `hadoop/scripts/enviar_hdfs.py`.

### 6. Consultas Analíticas em Apache Hive (1,5 páginas)
- Definição da tabela externa `integra_mercado.inteligencia_mercado_social` (`hive/criar_tabela.hql`) utilizando `OpenCSVSerde`.
- Apresentação e discussão das 5 consultas obrigatórias e 5 consultas adicionais implementadas em `hive/consultas.hql`.

### 7. Resultados e Recomendações para a Integra Engenharia de Sistemas (1,5 páginas)
- Síntese dos indicadores visualizados nas 3 abas do Dashboard Streamlit (`dashboard/app.py`).
- Recomendações práticas para a empresa a partir das tendências observadas no mercado (ex.: práticas de onboarding durante a implantação, transparência de SLA no suporte técnico, documentação de APIs de integração e melhoria contínua de usabilidade).
- *(Espaço reservado aos acadêmicos para relatar interações efetivamente realizadas com a organização parceira).*

### 8. Referências Técnicas (0,5 página)
- APACHE SOFTWARE FOUNDATION. *Apache Hadoop 3.2.1 Documentation (HDFS Architecture)*. Disponível em: https://hadoop.apache.org/docs/r3.2.1/.
- APACHE SOFTWARE FOUNDATION. *Apache Hive Language Manual (HiveQL & OpenCSVSerde)*. Disponível em: https://cwiki.apache.org/confluence/display/Hive/LanguageManual.
- APIFY TECHNOLOGIES. *Apify Platform & REST API v2 Documentation*. Disponível em: https://docs.apify.com/api/v2.
- McKINNEY, W. *Python for Data Analysis: Data Wrangling with pandas, NumPy, and Jupyter*. 3. ed. O'Reilly Media, 2022.
- STREAMLIT INC. *Streamlit Documentation*. Disponível em: https://docs.streamlit.io/.

---

## Parte 2 — Roteiro Sugerido para Apresentação Acadêmica (10 a 15 minutos)

1. **Contextualização e Problema (2 min):** Apresentar a Integra Engenharia de Sistemas, o vínculo com o projeto anterior (dados internos) e a proposta atual de inteligência de mercado multiplataforma (dados externos).
2. **Arquitetura e Coleta com Apify (3 min):** Mostrar `config/actors/` e `coleta/apify_client.py`, destacando os Actors reais do YouTube, Instagram e Reddit e a resiliência a falhas.
3. **Normalização e Classificação Heurística (2 min):** Demonstrar `processamento/normalizar_dados.py` e `processamento/classificar_dados.py`, enfatizando o tratamento correto de nulos e a conformidade com a LGPD.
4. **Armazenamento no HDFS e Consultas no Apache Hive (3 min):** Exibir `hadoop/scripts/enviar_hdfs.py`, a árvore `/projeto_integrador` no HDFS e a execução das 10 consultas de `hive/consultas.hql`.
5. **Demonstração ao Vivo do Dashboard Streamlit (3 min):** Navegar pelas 3 abas (`Visão Geral`, `Análise de Mercado` e `Detalhamento`), aplicando filtros interativos por plataforma, palavra-chave, sentimento e período.
