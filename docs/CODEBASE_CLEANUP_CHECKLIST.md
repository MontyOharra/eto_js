# Codebase Cleanup Checklist

Track file-by-file cleanup progress for the server codebase.

## Requirements

- Use Python 3.10+ typing syntax: `T | None` instead of `Optional[T]`, `list[T]` instead of `List[T]`, etc.
- Use Pydantic models for domain types (shared/types/)
- Reuse domain types in API schemas where possible (no duplicate definitions)
- Remove unnecessary mapper files when API uses domain types directly

## Workflow

- **IMPORTANT:** Re-read this document before AND after making any changes
- **IMPORTANT:** Check in with the user before making any code changes
- Commit after checking off each file or set of related files
- All cleanup work is done on the `code_cleanup` branch

---

## server/src/

- [x] `__init__.py`
- [ ] `app.py`

### api/

- [ ] `api/__init__.py`

#### api/mappers/
- [x] ~~`api/mappers/email_accounts.py`~~ (deleted - unnecessary)
- [x] ~~`api/mappers/email_ingestion_configs.py`~~ (deleted - unnecessary)
- [ ] `api/mappers/eto_runs.py`
- [ ] `api/mappers/modules.py`
- [ ] `api/mappers/order_management.py`
- [ ] `api/mappers/pdf_files.py`
- [ ] `api/mappers/pdf_templates.py`
- [ ] `api/mappers/pipelines.py`

#### api/routers/
- [ ] `api/routers/__init__.py`
- [ ] `api/routers/admin.py`
- [ ] `api/routers/auth.py`
- [x] `api/routers/email_accounts.py`
- [x] `api/routers/email_ingestion_configs.py`
- [ ] `api/routers/eto_runs.py`
- [ ] `api/routers/modules.py`
- [ ] `api/routers/order_management.py`
- [ ] `api/routers/pdf_files.py`
- [ ] `api/routers/pdf_templates.py`
- [ ] `api/routers/pipelines.py`
- [ ] `api/routers/system_settings.py`

#### api/schemas/
- [ ] `api/schemas/__init__.py`
- [x] `api/schemas/email_accounts.py`
- [x] `api/schemas/email_ingestion_configs.py`
- [ ] `api/schemas/eto_runs.py`
- [ ] `api/schemas/modules.py`
- [ ] `api/schemas/order_management.py`
- [ ] `api/schemas/output_channels.py`
- [ ] `api/schemas/pdf_files.py`
- [ ] `api/schemas/pdf_templates.py`
- [ ] `api/schemas/pipelines.py`
- [ ] `api/schemas/system_settings.py`

---

### features/

- [ ] `features/__init__.py`

#### features/auth/
- [ ] `features/auth/__init__.py`
- [ ] `features/auth/service.py`

#### features/email/
- [ ] `features/email/__init__.py`
- [x] `features/email/service.py`
- [x] `features/email/poller.py`
- [x] `features/email/processing.py`

##### features/email/integrations/
- [x] `features/email/integrations/__init__.py`
- [x] `features/email/integrations/base_integration.py`
- [x] `features/email/integrations/registry.py`
- [x] `features/email/integrations/standard_integration.py`

##### features/email/utils/
- [x] `features/email/utils/__init__.py`
- [x] `features/email/utils/deduplication.py`
- [x] `features/email/utils/filter_rules.py`

#### features/eto_runs/
- [ ] `features/eto_runs/__init__.py`
- [ ] `features/eto_runs/service.py`

##### features/eto_runs/utils/
- [ ] `features/eto_runs/utils/__init__.py`
- [ ] `features/eto_runs/utils/eto_worker.py`
- [ ] `features/eto_runs/utils/extraction.py`

#### features/htc_integration/
- [ ] `features/htc_integration/__init__.py`
- [ ] `features/htc_integration/service.py`
- [ ] `features/htc_integration/order_utils.py`
- [ ] `features/htc_integration/htc_order_worker.py`
- [ ] `features/htc_integration/address_utils.py`
- [ ] `features/htc_integration/attachment_utils.py`
- [ ] `features/htc_integration/lookup_utils.py`

#### features/modules/
- [ ] `features/modules/__init__.py`
- [ ] `features/modules/service.py`
- [ ] `features/modules/output_channel_definitions.py`

##### features/modules/utils/
- [ ] `features/modules/utils/__init__.py`
- [ ] `features/modules/utils/decorators.py`
- [ ] `features/modules/utils/registry.py`

##### features/modules/definitions/
- [ ] `features/modules/definitions/__init__.py`

###### features/modules/definitions/comparator/
- [ ] `features/modules/definitions/comparator/__init__.py`
- [ ] `features/modules/definitions/comparator/date_comparators.py`
- [ ] `features/modules/definitions/comparator/number_comparators.py`
- [ ] `features/modules/definitions/comparator/string_comparators.py`

###### features/modules/definitions/logic/
- [ ] `features/modules/definitions/logic/__init__.py`
- [ ] `features/modules/definitions/logic/boolean_and.py`
- [ ] `features/modules/definitions/logic/boolean_not.py`
- [ ] `features/modules/definitions/logic/boolean_or.py`
- [ ] `features/modules/definitions/logic/if_branch.py`
- [ ] `features/modules/definitions/logic/if_selector.py`

###### features/modules/definitions/misc/
- [ ] `features/modules/definitions/misc/__init__.py`
- [ ] `features/modules/definitions/misc/address_lookup.py`
- [ ] `features/modules/definitions/misc/address_name_swaps_lookup.py`
- [ ] `features/modules/definitions/misc/customer_picker.py`
- [ ] `features/modules/definitions/misc/generator.py`
- [ ] `features/modules/definitions/misc/next_order_number.py`
- [ ] `features/modules/definitions/misc/sql_lookup.py`

###### features/modules/definitions/output/
- [ ] `features/modules/definitions/output/__init__.py`
- [ ] `features/modules/definitions/output/basic_order_output.py`
- [ ] `features/modules/definitions/output/test_output.py`

###### features/modules/definitions/transform/
- [ ] `features/modules/definitions/transform/__init__.py`
- [ ] `features/modules/definitions/transform/address_parser.py`
- [ ] `features/modules/definitions/transform/data_duplicator.py`
- [ ] `features/modules/definitions/transform/datetime_extractor.py`
- [ ] `features/modules/definitions/transform/dim_builder.py`
- [ ] `features/modules/definitions/transform/dim_list_collector.py`
- [ ] `features/modules/definitions/transform/string_concatenate.py`
- [ ] `features/modules/definitions/transform/strip_text.py`
- [ ] `features/modules/definitions/transform/text_cleaner.py`
- [ ] `features/modules/definitions/transform/text_splitter.py`
- [ ] `features/modules/definitions/transform/text_strip.py`
- [ ] `features/modules/definitions/transform/type_converter.py`

#### features/order_management/
- [ ] `features/order_management/__init__.py`
- [ ] `features/order_management/service.py`

#### features/output_processing/
- [ ] `features/output_processing/__init__.py`
- [ ] `features/output_processing/service.py`

#### features/pdf_files/
- [ ] `features/pdf_files/__init__.py`
- [ ] `features/pdf_files/service.py`

##### features/pdf_files/utils/
- [ ] `features/pdf_files/utils/__init__.py`
- [ ] `features/pdf_files/utils/extraction.py`

#### features/pdf_templates/
- [ ] `features/pdf_templates/__init__.py`
- [ ] `features/pdf_templates/service.py`

#### features/pipeline_execution/
- [ ] `features/pipeline_execution/__init__.py`
- [ ] `features/pipeline_execution/service.py`

##### features/pipeline_execution/utils/
- [ ] `features/pipeline_execution/utils/__init__.py`

#### features/pipelines/
- [ ] `features/pipelines/__init__.py`
- [ ] `features/pipelines/service.py`

##### features/pipelines/utils/
- [ ] `features/pipelines/utils/__init__.py`
- [ ] `features/pipelines/utils/compilation.py`
- [ ] `features/pipelines/utils/validation.py`

---

### shared/

- [x] `shared/__init__.py`
- [x] `shared/logging.py`

#### shared/config/
- [x] `shared/config/__init__.py`
- [x] `shared/config/database.py`
- [x] `shared/config/storage.py`

#### shared/database/
- [ ] `shared/database/__init__.py`
- [ ] `shared/database/connection.py`
- [x] `shared/database/access_connection.py`
- [x] `shared/database/access_database_manager.py` (renamed from data_database_manager.py)
- [x] ~~`shared/database/database_manager.py`~~ (deleted - unused)
- [ ] `shared/database/models.py`
- [ ] `shared/database/unit_of_work.py`
- [ ] `shared/database/views.py`

##### shared/database/repositories/
- [ ] `shared/database/repositories/__init__.py`
- [ ] `shared/database/repositories/base.py`
- [x] `shared/database/repositories/email.py`
- [x] `shared/database/repositories/email_account.py`
- [x] `shared/database/repositories/email_ingestion_config.py`
- [ ] `shared/database/repositories/eto_run.py`
- [ ] `shared/database/repositories/eto_sub_run.py`
- [ ] `shared/database/repositories/eto_sub_run_extraction.py`
- [ ] `shared/database/repositories/eto_sub_run_output_execution.py`
- [ ] `shared/database/repositories/eto_sub_run_pipeline_execution.py`
- [ ] `shared/database/repositories/eto_sub_run_pipeline_execution_step.py`
- [ ] `shared/database/repositories/module.py`
- [ ] `shared/database/repositories/output_channel_type.py`
- [ ] `shared/database/repositories/pdf_file.py`
- [ ] `shared/database/repositories/pdf_template.py`
- [ ] `shared/database/repositories/pdf_template_version.py`
- [ ] `shared/database/repositories/pending_order.py`
- [ ] `shared/database/repositories/pending_order_history.py`
- [ ] `shared/database/repositories/pending_update.py`
- [ ] `shared/database/repositories/pending_update_history.py`
- [ ] `shared/database/repositories/pipeline_definition.py`
- [ ] `shared/database/repositories/pipeline_definition_step.py`
- [ ] `shared/database/repositories/system_settings.py`
- [ ] `shared/database/repositories/unified_actions.py`

#### shared/events/
- [ ] `shared/events/eto_events.py`
- [ ] `shared/events/order_events.py`

#### shared/exceptions/
- [ ] `shared/exceptions/__init__.py`
- [ ] `shared/exceptions/email.py`
- [ ] `shared/exceptions/output_execution.py`
- [ ] `shared/exceptions/pipeline_validation.py`
- [ ] `shared/exceptions/repository.py`
- [ ] `shared/exceptions/service.py`

#### shared/services/
- [ ] `shared/services/__init__.py`
- [x] ~~`shared/services/database_connection_pool.py`~~ (deleted - unused)
- [ ] `shared/services/service_container.py`

#### shared/types/
- [ ] `shared/types/__init__.py`
- [x] `shared/types/email.py`
- [x] `shared/types/email_accounts.py`
- [x] `shared/types/email_ingestion_configs.py`
- [x] `shared/types/email_integrations.py`
- [ ] `shared/types/eto_runs.py`
- [ ] `shared/types/eto_sub_runs.py`
- [ ] `shared/types/eto_sub_run_extractions.py`
- [ ] `shared/types/eto_sub_run_output_executions.py`
- [ ] `shared/types/eto_sub_run_pipeline_execution_steps.py`
- [ ] `shared/types/eto_sub_run_pipeline_executions.py`
- [ ] `shared/types/modules.py`
- [ ] `shared/types/output_channels.py`
- [ ] `shared/types/pdf_files.py`
- [ ] `shared/types/pdf_templates.py`
- [ ] `shared/types/pending_orders.py`
- [ ] `shared/types/pipeline_definition.py`
- [ ] `shared/types/pipeline_definition_step.py`
- [ ] `shared/types/pipeline_execution.py`
- [ ] `shared/types/pipelines.py`

#### shared/utils/
- [x] `shared/utils/__init__.py`
- [x] `shared/utils/datetime.py`

---

## Progress Summary

- **Total files:** 172 (2 deleted)
- **Completed:** 24
- **Remaining:** 148
