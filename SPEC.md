# SPEC — Criação em Lote de Processos via CSV (com Job Assíncrono)

> Especificação técnica derivada do [PRD.md](PRD.md). Define **como** implementar; o PRD define **o quê** e **por quê**.
>
> **Revisão atual:** o processamento foi convertido em **job assíncrono persistido em banco** para remover o limite de 500 linhas. O endpoint de upload retorna `202 Accepted` com `job_id`; o cliente acompanha o progresso via dois novos endpoints de leitura. As partes já funcionando (parser de CSV, dispatcher de INPI, classificação de erros, criação via `process_service`) **não foram alteradas em comportamento** — apenas envolvidas pelo job runner.

---

## 1. Resumo executivo

Endpoint `POST /api/v1/processes/batch-csv` recebe um CSV de `process_number`, **persiste um job** no banco com seus itens em estado `PENDING`, e dispara um worker em background que:

1. Consulta o portal pePI do INPI para obter o `title` de cada linha (via [inpi_pepi_service](app/services/inpi_pepi_service.py)).
2. Cria os processos via [process_service.create_process_with_validation](app/services/process_service.py#L33).
3. Atualiza o estado de cada item no banco em tempo real.

Cliente acompanha o job via `GET /api/v1/processes/batch-jobs/{job_id}` e `GET /api/v1/processes/batch-jobs/{job_id}/items?...`. Limite de 500 linhas é **removido**; permanece apenas um teto de bytes do upload (10 MB) para proteção de memória.

Entregáveis:

- 1 novo modelo + tabelas: `process_batch_job` e `process_batch_job_item` ([app/models/process_batch_job.py](app/models/process_batch_job.py)).
- 1 migration Alembic para criar as tabelas.
- 1 CRUD: [app/crud/crud_process_batch_job.py](app/crud/crud_process_batch_job.py).
- Novos schemas em [app/schemas/process.py](app/schemas/process.py) (jobs) — os schemas `BatchProcessItemResult` e `BatchProcessCsvResponse` existentes são **mantidos** e reusados como projeção dos itens persistidos.
- 1 service: [app/services/process_batch_service.py](app/services/process_batch_service.py) — refatorado para orquestrar via job, mas **mantém** `parse_csv` / `resolve_title` / `_classify_error` intactos.
- 3 handlers em [app/api/v1/endpoints/processes.py](app/api/v1/endpoints/processes.py) (upload + status + items).
- 1 hook de startup para reconciliar jobs órfãos (RUNNING após reboot).
- Testes unitários + integração (INPI mockado, BackgroundTasks executado inline).

---

## 2. Contrato HTTP

### 2.1 Upload — `POST /api/v1/processes/batch-csv`

```
POST /api/v1/processes/batch-csv
Content-Type: multipart/form-data
Authorization: Bearer <jwt>
```

| Campo          | Fonte | Tipo              | Validação                                                                                                                                   |
| -------------- | ----- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `company_id`   | Form  | `UUID`            | Obrigatório. Acesso validado via `access_control_service.validate_company_access(... 'create_processes')`.                                  |
| `process_type` | Form  | `ProcessTypeEnum` | Obrigatório. Um de `BRAND`, `PATENT`, `DESIGN`, `SOFTWARE`.                                                                                 |
| `file`         | File  | `UploadFile`      | Obrigatório. `.csv` ou `content_type` em `{text/csv, application/vnd.ms-excel, application/csv, application/octet-stream}`. Máx. **10 MB**. |

**Resposta `202 Accepted`:**

```python
class BatchProcessJobAccepted(BaseModel):
    job_id: UUID
    status: BatchJobStatusEnum  # sempre "PENDING" no momento do retorno
    total_rows: int
    company_id: UUID
    process_type: ProcessTypeEnum
    created_at: datetime
    status_url: str   # ex.: "/api/v1/processes/batch-jobs/{job_id}"
    items_url: str    # ex.: "/api/v1/processes/batch-jobs/{job_id}/items"
```

Comportamento do handler:

1. Valida content-type/extensão e tamanho do upload (415/413).
2. `parse_csv(content)` → `numbers` (lista). Sem mais limite de linhas; só pode falhar com `EMPTY_CSV` ou `INVALID_ENCODING` (400).
3. Valida acesso à company (403 se falhar; **antes** de gravar o job).
4. Cria registro `process_batch_job` (status `PENDING`, total = `len(numbers)`).
5. Em uma única transação, insere todos os `process_batch_job_item` com `status='PENDING'` e `row_index` preservando ordem.
6. Registra `BackgroundTasks.add_task(process_batch_service.run_job, job.id)`.
7. Retorna `202` com payload acima.

### 2.2 Status do job — `GET /api/v1/processes/batch-jobs/{job_id}`

Resposta `200`:

```python
class BatchJobStatusEnum(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"                 # tudo OK
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"                       # crash do worker; ver job.error

class BatchProcessJobResponse(BaseModel):
    id: UUID
    company_id: UUID
    process_type: ProcessTypeEnum
    status: BatchJobStatusEnum
    total_rows: int
    processed_rows: int
    created_count: int
    failed_count: int
    error: Optional[str] = None              # populado apenas se status=FAILED
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_by_user_id: UUID
    items_url: str
```

Acesso: usuário precisa ter `read_processes` na `company_id` do job (via `access_control_service.validate_company_access`). 404 se job não existe; 403 se sem acesso.

### 2.3 Itens do job — `GET /api/v1/processes/batch-jobs/{job_id}/items`

Query params: `skip` (default 0), `limit` (default 100, máx 500), `status_filter` (`pending|created|failed`, opcional).

Resposta `200`:

```python
class BatchJobItemsPage(BaseModel):
    job_id: UUID
    total: int                                # total de itens no job
    skip: int
    limit: int
    items: List[BatchProcessItemResult]       # schema já existente, com row_index opcional
```

`BatchProcessItemResult` recebe um campo opcional adicional `row_index: Optional[int]` (preserva ordem original do CSV; usado para clients que paginarem fora de ordem). Demais campos (`process_number`, `status`, `process_id`, `title`, `error`, `error_code`) são mantidos. O literal de `status` passa a ser `Literal["pending", "created", "failed"]`.

### 2.4 Tabela de status HTTP

| Código | Endpoint       | Condição                                                                                   |
| ------ | -------------- | ------------------------------------------------------------------------------------------ |
| `202`  | upload         | Job criado e agendado para execução.                                                       |
| `200`  | status / items | Leitura bem-sucedida.                                                                      |
| `400`  | upload         | CSV vazio (`EMPTY_CSV`) ou erro de decodificação (`INVALID_ENCODING`).                     |
| `403`  | qualquer       | Sem permissão na company (`create_processes` para upload, `read_processes` para leituras). |
| `404`  | status / items | Job não existe.                                                                            |
| `413`  | upload         | Arquivo > 10 MB.                                                                           |
| `415`  | upload         | Extensão/content-type fora do permitido.                                                   |
| `422`  | upload         | `process_type`/`company_id` inválidos; `file` ausente.                                     |

**Não há mais 502 “falha total INPI”**: como o processamento é assíncrono, o status `COMPLETED_WITH_ERRORS` com `error_code=INPI_UNAVAILABLE` em todos os itens já transmite a informação. Caller decide como reagir.

---

## 3. Arquivos a criar/modificar

### 3.1 [app/models/process_batch_job.py](app/models/process_batch_job.py) — **criar**

```python
class BatchJobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"

class BatchJobItemStatus(enum.Enum):
    PENDING = "PENDING"
    CREATED = "CREATED"
    FAILED = "FAILED"

class ProcessBatchJob(Base):
    __tablename__ = "process_batch_job"
    id                 = Column(UUID, primary_key=True, default=uuid.uuid4)
    company_id         = Column(UUID, ForeignKey("company.id"), nullable=False, index=True)
    created_by_user_id = Column(UUID, ForeignKey("user.id"), nullable=False, index=True)
    process_type       = Column(Enum(ProcessType, name="processtype"), nullable=False)
    status             = Column(Enum(BatchJobStatus, name="batchjobstatus"), nullable=False, default=BatchJobStatus.PENDING, index=True)
    total_rows         = Column(Integer, nullable=False)
    processed_rows     = Column(Integer, nullable=False, default=0)
    created_count      = Column(Integer, nullable=False, default=0)
    failed_count       = Column(Integer, nullable=False, default=0)
    error              = Column(Text, nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    started_at         = Column(DateTime(timezone=True), nullable=True)
    finished_at        = Column(DateTime(timezone=True), nullable=True)

    items = relationship("ProcessBatchJobItem", back_populates="job",
                         cascade="all, delete-orphan", order_by="ProcessBatchJobItem.row_index")

class ProcessBatchJobItem(Base):
    __tablename__ = "process_batch_job_item"
    id             = Column(UUID, primary_key=True, default=uuid.uuid4)
    job_id         = Column(UUID, ForeignKey("process_batch_job.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    row_index      = Column(Integer, nullable=False)            # 0-based, ordem do CSV
    process_number = Column(String(50), nullable=False)
    status         = Column(Enum(BatchJobItemStatus, name="batchjobitemstatus"),
                            nullable=False, default=BatchJobItemStatus.PENDING, index=True)
    process_id     = Column(UUID, ForeignKey("process.id", ondelete="SET NULL"), nullable=True)
    title          = Column(String(1000), nullable=True)
    error          = Column(String(200), nullable=True)
    error_code     = Column(String(32), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    job = relationship("ProcessBatchJob", back_populates="items")

    __table_args__ = (UniqueConstraint("job_id", "row_index"),)
```

> **Notas de schema:** `process_id` é `SET NULL` para não impedir delete do processo posteriormente; `job_id` é `CASCADE` para limpar itens junto. Índice composto `(job_id, status)` recomendado para o filtro do endpoint de itens.

### 3.2 Migration Alembic — **criar**

`alembic revision --autogenerate -m "add process_batch_job tables"`. Verificar manualmente que os enums `batchjobstatus` e `batchjobitemstatus` são criados via `sa.Enum(..., create_type=True)` (padrão deste projeto — ver [migrations existentes](MIGRATIONS.md)).

### 3.3 [app/crud/crud_process_batch_job.py](app/crud/crud_process_batch_job.py) — **criar**

Funções públicas:

```python
def create_job(db, *, company_id, user_id, process_type, process_numbers) -> ProcessBatchJob
def get_job(db, job_id: UUID) -> Optional[ProcessBatchJob]
def list_items(db, job_id: UUID, *, skip: int, limit: int, status_filter: Optional[BatchJobItemStatus]) -> tuple[List[ProcessBatchJobItem], int]
def mark_running(db, job: ProcessBatchJob) -> None                  # status + started_at
def mark_finished(db, job: ProcessBatchJob, *, final_status, error=None) -> None
def update_item_success(db, item: ProcessBatchJobItem, *, process_id, title) -> None
def update_item_failure(db, item: ProcessBatchJobItem, *, error_code, error) -> None
def increment_counters(db, job_id: UUID, *, created_delta=0, failed_delta=0) -> None
def find_orphan_running(db) -> List[ProcessBatchJob]                # hook de startup
```

`create_job` insere o job + todos os itens em **uma única transação** (`db.add_all(items); db.commit()`). Itens recebem `row_index` igual à posição na lista.

`increment_counters` usa `UPDATE ... SET processed_rows = processed_rows + 1, ...` em SQL bruto/`session.execute` para evitar race se evoluirmos para múltiplos workers. Por ora basta um UPDATE atômico por item.

### 3.4 [app/schemas/process.py](app/schemas/process.py) — **modificar**

- Adicionar `BatchJobStatusEnum`, `BatchJobItemStatusEnum`, `BatchProcessJobAccepted`, `BatchProcessJobResponse`, `BatchJobItemsPage`.
- `BatchProcessItemResult`: ampliar `status` para `Literal["pending", "created", "failed"]` e adicionar `row_index: Optional[int] = None`.
- Manter `BatchProcessCsvResponse` (não é mais retornado por nenhum endpoint, mas é usado por testes e por possível snapshot de relatório). Marcar como deprecated em comentário inline.

### 3.5 [app/services/process_batch_service.py](app/services/process_batch_service.py) — **modificar**

**Mantém intactos**: `parse_csv`, `resolve_title`, `_classify_error`. São o coração já testado da feature.

**Remove**: constante `MAX_ROWS` e o branch `if len(numbers) > MAX_ROWS: raise ValueError("TOO_MANY_ROWS")` em `parse_csv`. Aumentar `MAX_BYTES` para `10 * 1024 * 1024` (10 MB). A erro `TOO_MANY_ROWS` deixa de existir.

**Remove**: o método antigo `create_batch(...)` que processava de forma síncrona e devolvia `BatchProcessCsvResponse`. Deletar o método e suas chamadas (não há código em produção dependendo dele — o handler também muda nesta SPEC).

**Adiciona**:

```python
def enqueue_job(
    self,
    db: Session,
    *,
    company_id: UUID,
    process_type: ProcessTypeEnum,
    process_numbers: List[str],
    user: User,
    background_tasks: BackgroundTasks,
) -> ProcessBatchJob:
    """
    1. access_control_service.validate_company_access(db, user, company_id, 'create_processes')
    2. job = crud_process_batch_job.create_job(db, ...)  # PENDING + N itens PENDING
    3. background_tasks.add_task(self.run_job, job.id)
    4. return job
    """

def run_job(self, job_id: UUID) -> None:
    """
    Worker. Abre uma SessionLocal() própria (não reutiliza a do request).
    1. crud.mark_running(job)
    2. Para cada item PENDING (ordem por row_index):
         a. resolve_title -> title
         b. ProcessCreate(...) + process_service.create_process_with_validation
         c. update_item_success / update_item_failure
         d. increment_counters + commit por item (visibilidade incremental)
    3. Final: status COMPLETED se failed_count == 0,
              COMPLETED_WITH_ERRORS caso contrário.
       Em qualquer Exception não tratada do loop (DBAPI desconectado etc.),
       crud.mark_finished(status=FAILED, error=str(exc)[:500]).
    """

def reconcile_orphans(self) -> int:
    """
    Hook de startup. Marca jobs em status RUNNING como FAILED
    com error='Worker crashed before completion'. Retorna contagem.
    """
```

Convenções importantes do worker:

- **Sessão própria**: cada execução de `run_job` faz `db = SessionLocal(); try: ... finally: db.close()`. Não recebe `db` do handler porque o request já encerrou.
- **Commit por item**: o cliente que pollá o status vê `processed_rows` subindo em tempo real.
- **Sem transação global**: cada item é independente; falha de um não desfaz os demais.
- **Idempotência parcial**: se um item já não estiver `PENDING` (ex.: re-execução manual), pular.

### 3.6 [app/api/v1/endpoints/processes.py](app/api/v1/endpoints/processes.py) — **modificar**

Substituir o handler atual de `POST /batch-csv` por:

```python
@router.post(
    "/batch-csv",
    response_model=BatchProcessJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_processes_batch_csv(
    background_tasks: BackgroundTasks,
    company_id: UUID = Form(...),
    process_type: ProcessTypeEnum = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. valida extensão/content-type -> 415
    # 2. lê MAX_BYTES+1 -> 413 se excedeu
    # 3. parse_csv(content): ValueError("EMPTY_CSV"|"INVALID_ENCODING") -> 400
    # 4. job = process_batch_service.enqueue_job(db, ..., background_tasks=background_tasks)
    # 5. retorna BatchProcessJobAccepted com status_url/items_url
```

Adicionar dois novos handlers:

```python
@router.get("/batch-jobs/{job_id}", response_model=BatchProcessJobResponse)
def get_batch_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. job = crud.get_job(db, job_id); 404 se None
    # 2. access_control_service.validate_company_access(db, current_user, job.company_id, 'read_processes')
    # 3. retorna projeção do job

@router.get("/batch-jobs/{job_id}/items", response_model=BatchJobItemsPage)
def get_batch_job_items(
    job_id: UUID,
    skip: int = 0,
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[Literal["pending","created","failed"]] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # idem validação; retorna página ordenada por row_index ASC
```

Handlers permanecem **finos**: orquestram, mapeiam `ValueError` em `HTTPException`, delegam ao service.

### 3.7 [app/main.py](app/main.py) — **modificar**

Adicionar `@app.on_event("startup")` (ou lifespan) que invoca `process_batch_service.reconcile_orphans()` para fechar jobs `RUNNING` perdidos em crash/restart.

---

## 4. Mapeamento exceção → `error_code`

**Inalterado.** Roda dentro de `run_job` (worker), não no handler. `_classify_error` continua sendo a fonte da verdade:

| Exceção capturada                                     | `error_code`       | Nota                                                                                                 |
| ----------------------------------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------- |
| `ValueError` de `_parse_*_search_results` (não achou) | `NOT_FOUND`        | mensagem contém "não encontrado".                                                                    |
| `ValueError("NO_TITLE")` do dispatcher                | `NO_TITLE`         | título vazio ou < 5 chars.                                                                           |
| `requests.ConnectionError` / `Timeout` / `HTTPError`  | `INPI_UNAVAILABLE` | rede/5xx do pePI.                                                                                    |
| `HTTPException(400)` com detail "já está cadastrado"  | `DUPLICATE`        | `process_service` retorna 400 ([process_service.py:77-80](app/services/process_service.py#L77-L80)). |
| `HTTPException(422)` ou `HTTPException(400)` (outros) | `VALIDATION`       | regra de negócio.                                                                                    |
| Qualquer outra `Exception`                            | `INTERNAL`         | log WARNING com traceback; `error` = `str(exc)[:200]`.                                               |

Campo `error` continua limitado a 200 chars (cabe na coluna do banco).

---

## 5. Parsing do CSV — detalhes determinísticos

- Decodificação: `file_bytes.decode("utf-8-sig")` (absorve BOM). Falha → `ValueError("INVALID_ENCODING")` → 400.
- Parser: `csv.reader(io.StringIO(text), delimiter=",")`.
- Header detection: primeira linha **não-vazia**; se `row[0].strip().lower() == "process_number"`, descarta.
- Para cada linha subsequente: `row[0].strip()`; vazio → pula.
- Colunas adicionais ignoradas silenciosamente.
- Validação final:
  - `len == 0` → `ValueError("EMPTY_CSV")` → 400.
  - **Não há mais teto de linhas.** O upload é limitado por `MAX_BYTES` (10 MB) — suficiente para ~500k linhas de números típicos.

Não deduplicamos. Repetições no arquivo geram `DUPLICATE` na segunda ocorrência (constraint do banco via `validate_unique_process_number`).

---

## 6. Decisões fechadas

### 6.1 Processamento: assíncrono via `BackgroundTasks` + persistência em PostgreSQL

Não há Celery/Redis no projeto ([requirements.txt](requirements.txt)). `BackgroundTasks` do FastAPI executa após o response — adequado para um único worker uvicorn. Quando escalar para múltiplos workers, o estado já está no banco e a migração para Celery/RQ é mecânica (apenas trocar o `add_task`).

**Trade-off explícito:** se o processo morrer no meio do job, ele fica `RUNNING` até o `reconcile_orphans` do próximo startup marcá-lo como `FAILED`. Sem retry automático nesta fase.

### 6.2 Sem limite de linhas

Apenas o `MAX_BYTES = 10 MB` protege contra payload abusivo. Removidas a constante `MAX_ROWS` e a exceção `TOO_MANY_ROWS`.

### 6.3 “Falha total do INPI” → status `COMPLETED_WITH_ERRORS`, **não 502**

O caller polla o status e, se 100% dos items tiverem `error_code=INPI_UNAVAILABLE`, decide como reagir (UI pode oferecer “tentar novamente”). Não bloqueamos no servidor.

### 6.4 Rate limiting interno ao INPI

**Fora do escopo desta fase.** Worker chama o INPI sequencialmente sem `sleep`. Se gerar ban, mitigação posterior (reaproveitar sessão HTTP, backoff exponencial).

### 6.5 Endpoint company-oriented (`/companies/{company_id}/processes/batch-csv`)

**Fora do escopo.** Espelhar futuramente. O job já persiste `company_id`, então a migração futura é só de roteamento.

### 6.6 Retry e cancelamento de job

**Fora do escopo desta fase.** Itens em `FAILED` não são reprocessados automaticamente. Job em `RUNNING` não pode ser cancelado pelo cliente (nem por outro worker). Endpoints `POST /batch-jobs/{id}/retry` e `POST /batch-jobs/{id}/cancel` ficam para Fase 2.

---

## 7. Observabilidade

Logger: `intelectus.endpoints.processes.batch` (`logging.getLogger`).

Eventos:

- `INFO` no enqueue: `batch_enqueue job_id={} company_id={} type={} rows={} user_id={}`.
- `INFO` no início do worker: `batch_run_start job_id={} rows={}`.
- `INFO` por linha criada: `batch_item_ok job_id={} row={} process_number={} process_id={}`.
- `WARNING` por linha com falha: `batch_item_fail job_id={} row={} process_number={} error_code={} error={}`.
- `INFO` no fim: `batch_run_done job_id={} status={} created={} failed={} duration_ms={}`.
- `ERROR` se o worker crashar: `batch_run_crashed job_id={} error={}` + traceback; job vai para `FAILED`.
- `WARNING` no startup ao reconciliar: `batch_reconcile_orphan job_id={}` (uma linha por job órfão).

Sem PII (não logar email/nome). `user.id` é permitido.

---

## 8. Segurança

- Validar extensão e content-type **antes** de `file.read()`.
- Ler no máximo `MAX_BYTES + 1` bytes para detectar overflow sem consumir memória ilimitada.
- `company_id` sempre validado via `access_control_service.validate_company_access`:
  - `create_processes` no upload (e **antes** de criar o job).
  - `read_processes` nos endpoints de status/items.
- `process_service.create_process_with_validation` re-força `company_id` internamente ([process_service.py:62-68](app/services/process_service.py#L62-L68)).
- Job só é visível para usuários com acesso à `company_id` que ele referencia. Não vazar a existência de jobs de outras companies via 404 vs 403: retornar **403 antes de 404** quando o usuário não tem acesso. (Ordem prática: buscar job → se não existe, 404; se existe, validar acesso → 403 se inválido.)
- Limite de bytes (10 MB) protege a memória do servidor. O número de itens no banco é proporcional ao tamanho do CSV; tabela já indexada por `(job_id, status)` para evitar table scans em CSVs grandes.

---

## 9. Testes

### 9.1 [tests/services/test_process_batch_service.py](tests/services/test_process_batch_service.py)

`parse_csv` (inalterado, **menos** o teste de TOO_MANY_ROWS):

- ✅ com header `process_number\n942926668\n...`.
- ✅ sem header.
- ✅ com BOM (`\ufeff`).
- ✅ pula linhas em branco e strip de espaços.
- ✅ **novo**: 5.000 linhas → retorna lista com 5.000 (sem erro).
- ❌ CSV vazio → `ValueError("EMPTY_CSV")`.
- ❌ bytes não-UTF-8 → `ValueError("INVALID_ENCODING")`.
- ❌ ~~>500 linhas → TOO_MANY_ROWS~~ **removido**.

`resolve_title` (inalterado):

- ✅ BRAND/PATENT/SOFTWARE/DESIGN com mocks.
- ❌ `title=None | "" | <5 chars` → `ValueError("NO_TITLE")`.

`enqueue_job`:

- ✅ cria job em `PENDING` com `total_rows = len(numbers)` e N itens em `PENDING`.
- ✅ `BackgroundTasks.add_task` chamado com `run_job, job.id` (mock do BackgroundTasks).
- ❌ `validate_company_access` lança 403 → propaga, **nenhum job criado** no banco (assertCount 0).

`run_job`:

- ✅ 3 sucessos → status `COMPLETED`, contadores corretos, todos os items `CREATED`.
- ✅ mix 2 sucesso + 1 `NOT_FOUND` → `COMPLETED_WITH_ERRORS`, ordem preservada via `row_index`.
- ✅ duplicate na 2ª ocorrência do mesmo número → segundo item com `error_code=DUPLICATE`.
- ✅ `ConnectionError` → item `INPI_UNAVAILABLE`, **não interrompe restante**.
- ✅ todos `INPI_UNAVAILABLE` → status `COMPLETED_WITH_ERRORS` (nada de 502).
- ✅ commit por item: assertar que `processed_rows` cresce monotonicamente entre items (inspecionar no banco em meio à iteração via hook de teste).
- ✅ crash não tratado dentro do loop → status `FAILED`, `job.error` populado, demais items permanecem em `PENDING`.

`reconcile_orphans`:

- ✅ job em `RUNNING` com `started_at` antigo → vira `FAILED` com error de crash.
- ✅ jobs `PENDING`/`COMPLETED` permanecem inalterados.

### 9.2 [tests/api/test_processes_batch_csv.py](tests/api/test_processes_batch_csv.py)

- ✅ CSV válido (3 linhas, mock INPI) → 202 com `job_id`, `status="PENDING"`, `total_rows=3`. Após executar BackgroundTasks (TestClient executa inline), `GET /batch-jobs/{id}` → `COMPLETED`, `created_count=3`.
- ✅ CSV grande (1.000 linhas, INPI mockado retornando título válido) → 202; após processamento → `COMPLETED`, `created_count=1000`. Garante que limite de 500 foi removido.
- ❌ sem `file` → 422.
- ❌ `process_type="FOO"` → 422.
- ❌ arquivo > 10 MB → 413.
- ❌ extensão `.txt` → 415.
- ❌ usuário sem acesso à company → 403 e **nenhum job criado** no banco.
- ✅ `GET /batch-jobs/{job_id}` por outro user com acesso → 200.
- ❌ `GET /batch-jobs/{job_id}` por user sem acesso à company do job → 403.
- ❌ `GET /batch-jobs/{random_uuid}` → 404.
- ✅ `GET /batch-jobs/{id}/items?status=failed` → retorna apenas items com `status=failed`.
- ✅ `GET /batch-jobs/{id}/items?skip=10&limit=5` → paginação respeita ordem por `row_index`.

### 9.3 Convenções

Todos os testes mockam `inpi_pepi_service` (fixture `mock_inpi`). Para suíte de integração com BackgroundTasks: o `TestClient` do FastAPI executa `BackgroundTasks` antes de retornar do request, então testes podem assertar o estado pós-execução chamando o endpoint de status logo após o 202.

---

## 10. Critérios de aceitação

- [ ] `POST /api/v1/processes/batch-csv` aceita multipart com `company_id`, `process_type`, `file` e retorna **202 + job_id**.
- [ ] CSV com e sem header aceitos, sem limite de linhas (apenas 10 MB).
- [ ] `title` vem do INPI via `inpi_pepi_service` conforme `process_type` (lógica preservada).
- [ ] Processos criados têm **apenas** `process_number`, `title`, `process_type`, `company_id` preenchidos.
- [ ] Falha em uma linha não impede as demais; estado por linha persistido em `process_batch_job_item`.
- [ ] `GET /batch-jobs/{id}` retorna progresso em tempo real (`processed_rows`, contadores, `status`).
- [ ] `GET /batch-jobs/{id}/items` lista itens paginados, ordenados por `row_index`, com filtro por status.
- [ ] Usuário sem acesso → 403 antes de criar o job e antes de revelar existência via leitura.
- [ ] Após crash do processo, jobs em `RUNNING` ficam `FAILED` no próximo startup (`reconcile_orphans`).
- [ ] Migration Alembic gerada e revisada (enums + índices + FKs corretos).
- [ ] Testes unitários + integração verdes; INPI 100% mockado; teste explícito com >500 linhas.

---

## 11. Compatibilidade e migração

A SPEC anterior previa resposta síncrona `200 BatchProcessCsvResponse`. A nova retorna `202 BatchProcessJobAccepted`. Como o handler antigo está apenas em branch (ainda não merged em `main`), **não há clientes em produção dependendo do contrato anterior** — a quebra é apenas dentro do branch `feat-create-batch-process` e é absorvida nesta mesma SPEC.

Nada do que já estava implementado e funcionando é descartado:

- `parse_csv`, `resolve_title`, `_classify_error`: preservados textualmente, exceto a remoção do limite de 500.
- `BatchProcessItemResult`, `BatchProcessCsvResponse`: schemas mantidos (o primeiro é reutilizado no endpoint de items; o segundo permanece para uso futuro/relatório).
- Validações de upload (415/413/400), permissão (`validate_company_access`), e tabela de erro→código: preservadas integralmente.

---

## 12. Referências

- Endpoint atual de criação single: [app/api/v1/endpoints/processes.py:30-50](app/api/v1/endpoints/processes.py#L30-L50)
- Service INPI pePI: [app/services/inpi_pepi_service.py](app/services/inpi_pepi_service.py)
- Service de criação: [app/services/process_service.py:33-85](app/services/process_service.py#L33-L85)
- Router montado com prefixo `/processes`: [app/api/v1/api.py:12](app/api/v1/api.py#L12)
- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
