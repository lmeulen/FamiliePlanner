# LOGS

Full inventory of application logs across DEBUG, INFO, WARNING, ERROR, CRITICAL, and EXCEPTION levels.

- CRITICAL: 0
- ERROR: 11
- EXCEPTION: 7
- WARNING: 37
- INFO: 78
- DEBUG: 16

| Severity | Location | Message |
|---|---|---|
| DEBUG | app/routers/agenda.py:115 | Agenda recurrence series DB entity created. |
| DEBUG | app/routers/agenda.py:118 | Agenda recurrence series member relations updated. |
| DEBUG | app/routers/agenda.py:125 | Agenda recurrence occurrences generated. |
| DEBUG | app/routers/agenda.py:206 | Agenda recurrence occurrences regenerated after update. |
| DEBUG | app/routers/agenda.py:499 | Agenda event update request received. |
| DEBUG | app/routers/agenda.py:567 | Calendar subscription served from cache. |
| DEBUG | app/routers/meals.py:60 | meals.meal.create_request payload_date={} payload_dict={} |
| DEBUG | app/routers/photos.py:67 | Thumbnail generated: {} |
| DEBUG | app/routers/tasks.py:157 | Task recurrence series DB entity created. |
| DEBUG | app/routers/tasks.py:160 | Task recurrence series member relations updated. |
| DEBUG | app/routers/tasks.py:167 | Task recurrence occurrences generated. |
| DEBUG | app/routers/tasks.py:237 | Task recurrence occurrences regenerated after update. |
| DEBUG | app/routers/tasks.py:402 | Task update request received. |
| DEBUG | app/services/cozi_sync.py:181 | Cozi feed parsed into internal preview candidates. |
| DEBUG | app/utils/db.py:22 | set_junction_members table={} {}={} member_ids={} |
| DEBUG | app/utils/recurrence.py:58 | recurrence.rolling_window window_end={} |
| ERROR | app/main.py:209 | Database operation failed; returning 500. Check DB availability, schema state, and recent migrations. |
| ERROR | app/main.py:390 | Health probe failed: database unreachable. Service is degraded until DB connectivity is restored. |
| ERROR | app/routers/cozi.py:117 | Cozi import failed before completion. Inspect feed data consistency and database health before retry. |
| ERROR | app/routers/photos.py:114 | Thumbnail generation failed; original upload is kept and request continues. |
| ERROR | app/routers/recipes.py:63 | Mealie API request failed unexpectedly. Verify Mealie base URL, token validity, and network reachability. |
| ERROR | app/routers/settings.py:483 | Pre-restore backup creation failed; restore will continue without rollback snapshot. |
| ERROR | app/routers/settings.py:555 | Database restore failed; transaction rolled back and existing data was kept unchanged. |
| ERROR | app/routers/settings.py:584 | Weather provider rejected API key. Rotate/replace OPENWEATHER_API_KEY and retry. |
| ERROR | app/routers/settings.py:594 | Weather provider returned non-success status. Check provider availability and request parameters. |
| ERROR | app/routers/settings.py:610 | Weather request failed unexpectedly. Check network path, provider status, and API configuration. |
| ERROR | app/utils/db.py:30 | Failed to update member junction rows; relation update aborted and caller transaction should be reviewed. |
| EXCEPTION | app/backup_scheduler.py:60 | Nightly backup job failed; backup for this run was not created. Check disk space, permissions, and DB availability. |
| EXCEPTION | app/main.py:280 | Unhandled application exception; returning 500. Inspect traceback and upstream dependency health. |
| EXCEPTION | app/recurrence_scheduler.py:110 | Recurrence regeneration job failed; some infinite series may be outdated until next successful run. |
| EXCEPTION | app/routers/agenda.py:150 | Failed to create recurring agenda series; no data was committed. Validate recurrence parameters and member references. |
| EXCEPTION | app/routers/agenda.py:232 | Failed to update recurring agenda series; transaction rolled back. Check recurrence constraints and DB health. |
| EXCEPTION | app/routers/tasks.py:192 | Failed to create recurring task series; transaction rolled back. Validate recurrence payload and member assignments. |
| EXCEPTION | app/routers/tasks.py:263 | Failed to update recurring task series; transaction rolled back. |
| INFO | app/auth.py:31 | Authentication requirement setting changed. |
| INFO | app/auth.py:79 | Login succeeded; authenticated session created. |
| INFO | app/auth.py:94 | Logout completed; session cleared. |
| INFO | app/backup_scheduler.py:48 | Nightly backup scheduler started; waiting for next midnight run. |
| INFO | app/backup_scheduler.py:58 | Nightly backup file created successfully. |
| INFO | app/backup_scheduler.py:65 | Nightly backup scheduler stopped. |
| INFO | app/logging_config.py:79 | Logging initialised – level={}, log_dir={} |
| INFO | app/main.py:88 | Application startup initiated. |
| INFO | app/main.py:94 | Database initialization completed; service dependencies are ready. |
| INFO | app/main.py:115 | Application shutdown completed. |
| INFO | app/main.py:320 | HTTP request handled. |
| INFO | app/recurrence_scheduler.py:50 | Regenerated agenda occurrences for infinite recurrence series. |
| INFO | app/recurrence_scheduler.py:83 | Regenerated task occurrences for infinite recurrence series. |
| INFO | app/recurrence_scheduler.py:94 | Recurrence scheduler started; next run is daily at 01:00. |
| INFO | app/recurrence_scheduler.py:108 | Recurrence scheduler cycle completed successfully. |
| INFO | app/recurrence_scheduler.py:116 | Recurrence scheduler stopped. |
| INFO | app/routers/agenda.py:101 | Agenda recurrence series creation started. |
| INFO | app/routers/agenda.py:141 | Agenda recurrence series created successfully. |
| INFO | app/routers/agenda.py:183 | Agenda recurrence series update started. |
| INFO | app/routers/agenda.py:221 | Agenda recurrence series updated successfully. |
| INFO | app/routers/agenda.py:253 | Agenda recurrence series deleted. |
| INFO | app/routers/agenda.py:324 | Agenda event created. |
| INFO | app/routers/agenda.py:411 | Agenda event exported to ICS. |
| INFO | app/routers/agenda.py:511 | Agenda event updated. |
| INFO | app/routers/agenda.py:546 | Agenda event deleted. |
| INFO | app/routers/agenda.py:637 | Calendar subscription generated and cached. |
| INFO | app/routers/birthdays.py:129 | birthdays.created id={} name='{}' year_type={} |
| INFO | app/routers/birthdays.py:176 | birthdays.updated id={} name='{}' year_type={} |
| INFO | app/routers/birthdays.py:184 | birthdays.deleted id={} |
| INFO | app/routers/cozi.py:84 | Cozi preview generated successfully. |
| INFO | app/routers/cozi.py:125 | Cozi import completed. |
| INFO | app/routers/cozi.py:167 | Cozi UID linked to existing FamiliePlanner item. |
| INFO | app/routers/family.py:31 | family.member.created id={} name='{}' |
| INFO | app/routers/family.py:44 | family.member.updated id={} name='{}' |
| INFO | app/routers/family.py:70 | family.member.deleted id={} |
| INFO | app/routers/grocery.py:53 | grocery.category.created id={} name='{}' |
| INFO | app/routers/grocery.py:65 | grocery.categories.reordered count={} |
| INFO | app/routers/grocery.py:109 | grocery.category.deleted id={} name='{}' (items moved to category_id={}) |
| INFO | app/routers/grocery.py:179 | grocery.item.created id={} product='{}' category={} |
| INFO | app/routers/grocery.py:204 | grocery.item.updated id={} checked={} |
| INFO | app/routers/grocery.py:214 | grocery.items.cleared_done count={} |
| INFO | app/routers/grocery.py:244 | grocery.item.deleted id={} |
| INFO | app/routers/meals.py:65 | meals.meal.created id={} name='{}' date={} saved_date={} |
| INFO | app/routers/meals.py:89 | meals.meal.updated id={} name='{}' |
| INFO | app/routers/meals.py:116 | meals.meal.deleted id={} |
| INFO | app/routers/photos.py:128 | photos.uploaded id={} filename='{}' (with thumbnail) |
| INFO | app/routers/photos.py:158 | photos.deleted id={} filename='{}' (including thumbnail) |
| INFO | app/routers/recipes.py:192 | recipes.recipe.created slug={} |
| INFO | app/routers/recipes.py:248 | recipes.recipe.updated slug={} |
| INFO | app/routers/recipes.py:264 | recipes.recipe.patched slug={} |
| INFO | app/routers/recipes.py:273 | recipes.recipe.deleted slug={} |
| INFO | app/routers/recipes.py:288 | recipes.recipe.image_uploaded slug={} |
| INFO | app/routers/search.py:139 | search query='{}' results={} |
| INFO | app/routers/settings.py:167 | Application settings updated via API request. |
| INFO | app/routers/settings.py:234 | Database backup export started. |
| INFO | app/routers/settings.py:246 | Database backup export completed. |
| INFO | app/routers/settings.py:407 | Pre-restore safety backup prepared. |
| INFO | app/routers/settings.py:427 | Database restore request received. |
| INFO | app/routers/settings.py:455 | Database restore dry-run completed. |
| INFO | app/routers/settings.py:540 | Database restore completed successfully. |
| INFO | app/routers/stats.py:35 | stats.fetch period={} |
| INFO | app/routers/stats.py:161 | stats.completed period={} task_completions={} cooking={} meals={} events_per_week={} |
| INFO | app/routers/tasks.py:79 | Task list created. |
| INFO | app/routers/tasks.py:91 | Task list ordering updated. |
| INFO | app/routers/tasks.py:108 | Overdue section position updated. |
| INFO | app/routers/tasks.py:122 | Task list updated. |
| INFO | app/routers/tasks.py:134 | Task list deleted. |
| INFO | app/routers/tasks.py:143 | Task recurrence series creation started. |
| INFO | app/routers/tasks.py:183 | Task recurrence series created successfully. |
| INFO | app/routers/tasks.py:219 | Task recurrence series update started. |
| INFO | app/routers/tasks.py:252 | Task recurrence series updated successfully. |
| INFO | app/routers/tasks.py:281 | Task recurrence series deleted. |
| INFO | app/routers/tasks.py:367 | Overdue tasks marked complete for date. |
| INFO | app/routers/tasks.py:380 | Task created. |
| INFO | app/routers/tasks.py:412 | Task updated. |
| INFO | app/routers/tasks.py:427 | Task completion status toggled. |
| INFO | app/routers/tasks.py:461 | Task deleted. |
| INFO | app/services/cozi_sync.py:563 | Cozi import sync cycle committed to database. |
| WARNING | app/auth.py:82 | Login attempt rejected due to invalid credentials. Monitor repeated failures for brute-force attempts. |
| WARNING | app/main.py:145 | Request validation failed; returning 422. Verify request payload schema and required fields. |
| WARNING | app/main.py:187 | Database integrity check failed; returning 422. Inspect foreign keys, unique constraints, and duplicate inputs. |
| WARNING | app/main.py:257 | HTTP error returned to client. Confirm endpoint/path, authorization, and request parameters. |
| WARNING | app/main.py:438 | Browser reported CSP violation; request was blocked by policy. Review CSP config if this blocks expected resources. |
| WARNING | app/routers/agenda.py:163 | Requested agenda recurrence series was not found. Verify series_id and client cache freshness. |
| WARNING | app/routers/agenda.py:177 | Requested agenda recurrence series was not found during update. Verify series_id and whether it was deleted by another user. |
| WARNING | app/routers/agenda.py:244 | Requested agenda recurrence series was not found for deletion. |
| WARNING | app/routers/agenda.py:336 | Requested agenda event was not found. |
| WARNING | app/routers/agenda.py:352 | Requested agenda event export failed because the event was not found. |
| WARNING | app/routers/agenda.py:494 | Requested agenda event update failed because the event was not found. |
| WARNING | app/routers/agenda.py:528 | Administrative bulk delete executed: all agenda events and recurrence series were removed. |
| WARNING | app/routers/agenda.py:539 | Requested agenda event delete failed because the event was not found. |
| WARNING | app/routers/birthdays.py:152 | Administrative bulk delete executed: all birthdays and linked agenda recurrence series were removed. |
| WARNING | app/routers/cozi.py:75 | Cozi preview could not be generated because feed retrieval/parsing failed. Verify Cozi URL and network reachability. |
| WARNING | app/routers/family.py:60 | Administrative bulk delete executed: all family members were removed and member links were cascaded. |
| WARNING | app/routers/grocery.py:228 | Administrative bulk delete executed: all grocery items and category-learning history were removed. |
| WARNING | app/routers/meals.py:74 | Meal record not found. |
| WARNING | app/routers/meals.py:83 | Meal record not found for update request. |
| WARNING | app/routers/meals.py:101 | Administrative bulk delete executed: all meals were removed. |
| WARNING | app/routers/meals.py:112 | Meal record not found for delete request. |
| WARNING | app/routers/recipes.py:304 | Categories endpoint unavailable on Mealie; returning empty category list. |
| WARNING | app/routers/recipes.py:324 | Tags endpoint unavailable on Mealie; returning empty tag list. |
| WARNING | app/routers/settings.py:319 | Skipped invalid junction-table row during restore; restore continues in degraded mode for this relation. |
| WARNING | app/routers/settings.py:474 | Backup validation warning detected; restore will continue because warning is non-fatal. |
| WARNING | app/routers/settings.py:569 | Weather request rejected because API key is missing. Configure OPENWEATHER_API_KEY before retrying. |
| WARNING | app/routers/tasks.py:116 | Task list not found for update request. |
| WARNING | app/routers/tasks.py:130 | Task list not found for delete request. |
| WARNING | app/routers/tasks.py:205 | Task recurrence series not found. |
| WARNING | app/routers/tasks.py:216 | Task recurrence series not found during update. |
| WARNING | app/routers/tasks.py:275 | Task recurrence series not found for deletion. |
| WARNING | app/routers/tasks.py:390 | Task not found. |
| WARNING | app/routers/tasks.py:400 | Task not found for update request. |
| WARNING | app/routers/tasks.py:421 | Task not found for toggle request. |
| WARNING | app/routers/tasks.py:446 | Administrative bulk delete executed: all tasks, task lists, and recurrence series were removed. |
| WARNING | app/routers/tasks.py:457 | Task not found for delete request. |
| WARNING | app/utils/crud.py:38 | Requested resource was not found in database. |
