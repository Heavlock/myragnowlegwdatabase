# Repository-local agent skills

Use English for agent responses by default, unless the user explicitly requests another language.

For requests to operate this myrag knowledge database, read the matching local skill:

| User intent | Skill |
| --- | --- |
| Save new information for later retrieval | [myrag-save](.agents/skills/myrag-save/SKILL.md) |
| Correct/update a known stored document | [myrag-update](.agents/skills/myrag-update/SKILL.md) |
| Search stored information or read a document | [myrag-search](.agents/skills/myrag-search/SKILL.md) |
| Prepare/start/verify the local application | [myrag-install](.agents/skills/myrag-install/SKILL.md) |

The [knowledge contracts](docs/knowledge-contracts.md) define profile selection, save/update/search semantics, read-back verification, and the repository client. Use these local contracts for this repository even if an older user-level myrag skill is installed. Routine code/documentation work does not imply saving its contents to the knowledge database.

Use the selected database profile; PostgreSQL is the documented default. The two profiles are separate knowledge stores. Update is full document replacement at the server: read the complete document, preserve unrequested fields, and keep its ID. Use the repository client when no connected MCP tool is known to target the selected endpoint.

Keep changes and skill configuration local to this repository. Do not install these skills globally, change the laptop's global skills, commit, or push unless the user requests the corresponding action. Tests that need writes should use disposable projects/volumes rather than the user's working knowledge store.

Keep the root README focused on installation, configuration, operation, and testing. Put session history, implementation progress, and measured run details in reports or specialized documentation.
