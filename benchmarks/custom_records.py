"""Original fictional articles and held-out retrieval questions for EXTRA v1.

Records are authored before retrieval evaluation; no model scores inform labels.
Each question is supported by the paragraph with the same index.
"""
RECORDS = []


def add(cluster, title, paragraphs, queries):
    assert len(paragraphs) == len(queries) == 3
    RECORDS.append({'cluster':cluster,'title':title,'paragraphs':paragraphs,'queries':queries})

# ACCESS AND IDENTITY
add('access', 'Employee account activation', [
 'Aster Works opens an employee identity only after People Operations confirms the start date and a manager selects a role bundle. The service desk creates a pending record from that approved request. A personal message from the recruit is not sufficient to activate the identity.',
 'The activation invitation is sent to the verified personal address recorded by People Operations. It expires after forty-eight hours. An unused invitation can be replaced without creating another employee record; the previous link becomes invalid when the replacement is issued.',
 'Some employees arrive with an old contractor login. The service desk links the old identity to the employee record and reviews its groups before enabling the employee role bundle. It must not create a second identity simply because the person changed employment status.'
], [
 'What approvals are needed before a new employee can activate an account?',
 'A recruit waited three days before opening the welcome link. How should support let them join?',
 'Someone becoming an employee already has a contractor login. Should the service desk create another identity?'
])
add('access', 'Time-limited contractor access', [
 'A contractor sponsor requests access with a named project, an external employer, and a definite end date. The sponsor chooses only the project groups the contractor needs. General employee bundles are not available through the contractor request form.',
 'Contractor access automatically stops at the end date, even if the project is still running. The sponsor can request an extension before expiry. A project owner must approve the new period; opening a support chat does not extend an expiring assignment.',
 'A sponsor who leaves the company must hand the assignment to another employee. Without a replacement sponsor, contractor access is suspended at the next daily review. Completing the sponsor handoff preserves the existing identity and its audit history.'
], [
 'What information must a sponsor include in a contractor access request?',
 'An outside worker still needs the project after their permission period ends. How can that period be continued?',
 'The employee responsible for an external consultant has left. How can the consultant retain authorized access?'
])
add('access', 'Lost second-factor device recovery', [
 'An employee who loses the phone used for sign-in opens an identity recovery case from a known contact address. Support verifies the person through a live callback and manager confirmation. A screenshot of an old login page does not establish ownership.',
 'After verification, support disables the missing second-factor device and issues a one-use enrollment link valid for twenty minutes. The employee registers a replacement factor during that window. The link cannot be used as a permanent substitute for a registered factor.',
 'If the missing phone also contains active company sessions, support revokes those sessions before enabling the replacement factor. The recovery case records both actions separately. Enrolling another phone alone does not invalidate sessions already present on the lost device.'
], [
 'How does support verify an employee who has lost their sign-in phone?',
 'I cannot generate the login codes anymore. What temporary route lets me register a new authenticator?',
 'A lost phone has both the authenticator and open company sessions. What extra action is required during recovery?'
])
add('access', 'Emergency administrator entry', [
 'The emergency administrator identity is reserved for an outage of the normal identity provider. An incident commander and a second responder jointly authorize its use. It is not an alternative for someone waiting on a routine permission request.',
 'Emergency credentials are released from a sealed vault record and must be rotated immediately after the session. The responder records the commands and the reason normal entry was unavailable. A successful repair does not remove the obligation to rotate the credential.',
 'If ordinary employee login still works but one project administrator is absent, the team uses temporary privilege elevation instead. The emergency identity must remain sealed in that situation. The distinction is whether the shared identity service is unavailable, not whether the work is urgent.'
], [
 'Who must authorize use of the emergency administrator identity?',
 'Normal sign-in is down and we used the sealed credential to repair it. What must happen after the session?',
 'The project administrator is away, but employee login works. Is emergency administrator entry the right route?'
])
add('access', 'Nonhuman service identity ownership', [
 'Aster Works gives each automated service its own nonhuman identity with a named team owner and a documented purpose. A service identity cannot be owned solely by an individual employee. Interactive employee sign-in is disabled for these identities.',
 'The owner records each consuming workload in the service identity inventory. Before retiring an identity, the team checks those consumers and moves any remaining workload to another approved identity. An empty employee membership list is not evidence that a service identity is unused.',
 'When ownership moves between teams, the receiving team accepts the inventory record before the old owner is removed. Credentials are rotated as part of the handoff. A team rename by itself does not justify deleting the identity and losing its historical audit trail.'
], [
 'What ownership information is required for an automated service account?',
 'An account has no people assigned to it. How do we establish whether any background jobs still depend on it?',
 'Another team is taking responsibility for a running service. How should its machine identity be transferred?'
])
add('access', 'Overlapping API credential rotation', [
 'Application owners rotate integration credentials by issuing a second key while the first remains valid. They deploy the new key to every registered consumer, then check successful authenticated requests. Revoking the first key before that check can interrupt running integrations.',
 'The overlap window is limited to one working day. The old key is disabled after all consumers pass verification, and the change record captures both key identifiers without recording their secret values. Creating a second key is the beginning of rotation, not its completion.',
 'A suspected stolen key does not receive the ordinary overlap window. The owner follows the leaked-secret incident procedure and revokes the exposed credential immediately. The routine rotation guide applies only when the old key is still considered confidential.'
], [
 'How can an integration rotate its API key without interrupting consumers?',
 'We deployed a replacement credential successfully. When do we remove the previous one, and what gets recorded?',
 'An API key may have been stolen. Should the owner leave it valid during the normal rotation overlap?'
])
add('access', 'Temporary privilege elevation', [
 'An employee needing a short administrative task requests a named permission, a reason, and a maximum four-hour window. The resource owner approves that request. Approval grants only the requested permission and does not replace the employee normal role bundle.',
 'The elevation expires automatically and the employee receives a reminder thirty minutes before it ends. If the task runs longer, the owner must approve a new request. Keeping a terminal open does not preserve the administrative permission after expiry.',
 'Repeated need for the same elevated permission is reviewed as a role-design issue. Three requests for the same resource within a week are sent to the access steward. The steward evaluates a suitable standing role instead of silently extending a temporary grant.'
], [
 'What must an employee request to obtain temporary administrative permission?',
 'My short-lived admin window is about to close while a task is unfinished. How can I continue with authorization?',
 'A teammate needs the same elevated right several times every week. Which process reviews a more durable role?'
])
add('access', 'Employee departure access shutdown', [
 'People Operations schedules a departing employee identity for shutdown at an approved departure time. At that time the identity service blocks new login, revokes active sessions, and removes group memberships. A manager request to keep receiving mail does not preserve the former employee login.',
 'Business records remain assigned to their projects after a departure. A manager nominates a new owner for shared documents and open service assignments. Mail forwarding, where approved, uses a separate routing rule rather than sharing the departed employee password.',
 'An urgent departure can be initiated by the duty people partner before the regular batch runs. The service desk confirms shutdown completion and records the actual time. Equipment return is tracked separately and must not delay revocation of the departing identity.'
], [
 'Which access actions occur when an employee departure reaches its scheduled time?',
 'How can a manager preserve business correspondence and shared records after someone leaves without keeping their login alive?',
 'A departure needs to take effect immediately, but the laptop has not been returned. Can identity shutdown proceed?'
])
add('access', 'Quarterly access certification', [
 'Every quarter, resource owners receive the current list of people and service identities with access to their resources. They certify each entry against a present business need. Checking only that a person is still employed is not sufficient evidence of continued need.',
 'An owner can approve, revoke, or request clarification for an entry. Clarification remains unresolved until an explanation is recorded. Entries left unresolved for ten working days are removed from the resource rather than automatically treated as approved.',
 'A review can reveal an identity belonging to a former team member whose employee account is still active elsewhere. The resource owner removes the obsolete resource membership, while People Operations leaves the person overall employee identity intact. Resource certification is narrower than employee departure.'
], [
 'What should resource owners verify during the quarterly access review?',
 'What happens to a permission whose business justification remains unanswered during certification?',
 'An active employee changed teams and no longer needs one resource. Should certification disable their entire employee account?'
])
add('access', 'Unattended laptop containment', [
 'An employee who cannot locate a company laptop reports the asset identifier and the last known location to the device desk. The desk marks the asset missing and prevents it from obtaining new device-trust tokens. This action concerns the computer, not the employee identity.',
 'A remote lock is queued for the next time the laptop contacts device management. If the device remains offline, the lock is pending and cannot be reported as completed. The desk can still invalidate existing device-trust tokens while waiting for contact.',
 'If the laptop is found before it receives a remote erase, the device desk verifies its serial number and physical custody before restoring trust. Finding the computer does not automatically restore its tokens. The desk records recovery separately from closing any identity-factor recovery case.'
], [
 'What information should an employee provide when a company laptop goes missing?',
 'Can support claim that a remote lock succeeded while the missing computer has never reconnected?',
 'A missing laptop was recovered without being erased. What has to happen before it is trusted again?'
])

# BACKUP AND RECOVERY
add('recovery', 'Database point-in-time restoration', [
 'The database team handles an accidental row change by restoring a disposable database to a selected time before the mistake. The requester supplies the database name, incident time, and affected records. A disposable restore is inspected before any recovered data is written into the live service.',
 'Recovery uses a base backup together with the continuous transaction log. A base backup alone cannot select an arbitrary moment between backup runs. The database team checks that the log sequence covers the requested time before promising that the desired state can be reconstructed.',
 'When one customer record was deleted but other customers continued making valid changes, the team extracts that record from the disposable restore. It does not replace the whole live database with yesterday state. The extraction preserves unrelated updates made after the incident.'
], [
 'What information is needed to restore a database to a time before an accidental change?',
 'Why can yesterday backup alone fail to reproduce the database at a particular minute this morning?',
 'Only one customer record was accidentally deleted while other users kept working. How should recovery preserve their later changes?'
])
add('recovery', 'Deleted shared-file recovery', [
 'The document service retains deleted shared files in a recoverable bin for thirty days. A project owner requests recovery with the original folder, filename, and approximate deletion time. Recovering a file restores its content but does not automatically reopen every old sharing link.',
 'If a file with the same name now exists in the original folder, recovery creates a sibling with a recovery suffix. The service does not overwrite the newer file. The owner compares both versions and decides which one should remain the working copy.',
 'A request after the recoverable-bin period is escalated to the backup team with no guarantee of success. Retention extensions must have existed before deletion. Asking to place an already-expired file on hold cannot recreate content that is no longer retained.'
], [
 'How long can a project owner recover a deleted shared file from the recoverable bin?',
 'Will undeleting a document replace a newer item that now has the same name?',
 'A shared file was deleted more than thirty days ago. Can a newly requested hold guarantee its restoration?'
])
add('recovery', 'Recovery-site activation', [
 'A recovery-site activation is considered when the primary facility is unavailable and ordinary service repair cannot meet the incident recovery target. The incident commander authorizes the move after the infrastructure lead verifies the state of replicated data. A single damaged application server is not sufficient reason to move the entire service.',
 'The team records the last replicated transaction and publishes a recovery checkpoint before changing traffic routing. Users are told the checkpoint so they can recognize work that might need to be repeated. Routing traffic first and estimating the data position later is not permitted.',
 'Returning to the primary facility is a separately scheduled change. New writes at the recovery site must be reconciled before traffic is moved back. The primary facility becoming reachable does not by itself make an immediate return safe.'
], [
 'Who approves moving a service to the recovery site during a facility outage?',
 'What data-position information should be established before users are routed to the standby facility?',
 'The original facility is reachable again after a recovery-site move. Can traffic return before new writes are reconciled?'
])
add('recovery', 'Backup integrity exception handling', [
 'The backup monitor compares stored backup manifests with their recorded checksums. A mismatch marks the affected backup as suspect and opens an integrity exception. The file remains retained for investigation, but it is removed from the list of eligible restore sources.',
 'The backup team checks a separate retained copy and performs a sample restore before clearing the exception. Copying the suspect file to another location does not establish that it is healthy. The replacement source must pass both checksum verification and the sample recovery.',
 'An integrity exception on one backup does not authorize deleting every backup for the database. Healthy retained copies remain available and their retention clocks continue normally. Broad deletion could remove the independent recovery path needed to investigate the damaged copy.'
], [
 'What happens when a stored backup fails its manifest checksum check?',
 'What checks are needed before a separate backup copy can replace a suspected damaged one?',
 'One database backup is corrupt. Should the team delete the other retained copies as part of the exception?'
])
add('recovery', 'Quarterly restoration exercise', [
 'Each service owner schedules a restoration exercise every quarter using an isolated test environment. The exercise selects a retained backup without changing the production service. Its purpose is to demonstrate recovery, not merely show that a backup file exists in storage.',
 'The observer records restoration duration, the recovered checkpoint, and application-level checks performed by the service owner. A successful file download does not count as a completed exercise. The application must read representative recovered records and complete its basic verification workflow.',
 'If the exercise misses the agreed recovery target, the team opens a corrective action with an owner and a due date. The exercise record remains a failure until a repeat demonstration passes. Renaming the backup job does not resolve an observed recovery-time problem.'
], [
 'Where and how often should a service demonstrate restoration from a retained backup?',
 'What must be checked beyond downloading a backup before a recovery rehearsal counts as successful?',
 'A restoration rehearsal finishes too slowly. Can it be recorded as passing while improvements are still pending?'
])
add('recovery', 'Preservation hold on backup sets', [
 'A preservation hold is a retention instruction attached to identified backup sets by the records steward. The request specifies the service, date range, and case reference. The hold prevents scheduled expiry for the selected material; it does not grant anyone new permission to inspect the data.',
 'Backup operators verify that the selected sets still exist before acknowledging a hold. Material already removed by an earlier expiry cannot be promised as preserved. The acknowledgment lists the actual retained sets rather than simply repeating the requested date range.',
 'Only the records steward can release a preservation hold after the owning case is closed. The ordinary retention policy then resumes for the affected sets. An application owner request for cheaper storage is not sufficient to release an active hold.'
], [
 'What information identifies the backup sets covered by a preservation hold?',
 'Can an operator acknowledge that an already-expired backup is preserved just because its date appears in a new request?',
 'Who can release a backup preservation hold when an application owner wants to reduce storage costs?'
])
add('recovery', 'Backup encryption-key transition', [
 'The storage team introduces a new backup encryption key for future backup sets while retaining access to keys needed by older sets. Changing the active writing key does not re-encrypt all historical backups. Each retained set keeps a reference to the key that can read it.',
 'Before retiring an old key, the team inventories every retained backup that references it and performs a restore check. The key remains available while any required retained set depends on it. A key age alone is not sufficient evidence that it is safe to remove.',
 'If an old key is suspected of exposure, the incident team assesses affected retained sets and creates replacement protected copies where required. This emergency path is separate from routine key retirement. Operators must not destroy the only readable key before an approved recovery path exists.'
], [
 'Does changing the active backup-writing key automatically re-encrypt historical backup sets?',
 'How can the storage team determine whether an older decryption key is still needed?',
 'An old backup key may be exposed. Should operators immediately destroy it if retained backups still depend on it?'
])
add('recovery', 'Clean-room ransomware restoration', [
 'The incident team performs ransomware recovery in a clean-room network that is disconnected from ordinary employee devices. The team chooses a recovery point from before the suspected compromise. A recent backup is not automatically suitable if it may already contain attacker changes.',
 'Recovered servers receive new administrative credentials and pass malicious-file checks before they can contact production networks. The clean-room coordinator records these gates for each server. Restoring files successfully does not authorize bypassing credential replacement or inspection.',
 'If the recovered application requires data created after the clean recovery point, specialists inspect and transfer selected records through the approved import gate. They do not attach the compromised system disk to the rebuilt server. This separation preserves the trust boundary of the clean environment.'
], [
 'What recovery environment is required after a ransomware compromise?',
 'What must a restored server pass before it can reconnect to the normal production network?',
 'Some useful records were created after the clean recovery point. How can they be recovered without attaching a compromised disk?'
])
add('recovery', 'Backup retention tier assignment', [
 'Service owners assign each backup job a standard or extended retention tier when the job is registered. The standard tier keeps daily sets for thirty days, while the extended tier retains monthly sets for twelve months. The selected tier is recorded with the service inventory.',
 'A tier change applies to future backup sets unless the storage steward approves an explicit reassignment of existing sets. Raising retention today does not recreate a backup that expired yesterday. Owners check available history before promising an older restore date to a customer.',
 'The extended tier is intended for services with a documented long-history need. It is not a substitute for a preservation hold tied to a specific case. A hold can protect selected sets regardless of the job standard tier and must be released through its own process.'
], [
 'How do the standard and extended backup retention tiers differ?',
 'Can moving a backup job to a longer history tier bring back a set that has already expired?',
 'A specific investigation requires keeping selected backup sets. Is changing the entire job to extended retention equivalent to a case hold?'
])
add('recovery', 'Backup-job completion verification', [
 'A backup job is complete only when the worker has uploaded its data, written a manifest, and received a catalog acknowledgment. A scheduler message that the worker started is not a completion signal. Monitoring reads the catalog state rather than relying solely on process exit notifications.',
 'If a worker exits successfully but the catalog acknowledgment is missing, the job remains unverified. The operator checks the upload and registration records before rerunning anything. A second blind run can create confusion about which set belongs to the original scheduled checkpoint.',
 'An unverified job is distinct from a backup with a failed checksum. The former lacks proof of registration; the latter is registered but has an integrity exception. Operators route those cases to different queues instead of marking both as an undifferentiated successful backup.'
], [
 'What evidence establishes that a scheduled backup job has completed?',
 'The backup process exited without error, but its catalog acknowledgment is missing. Should monitoring mark the job successful?',
 'How does an unregistered backup run differ from a registered set that fails its checksum?'
])

# NETWORK AND DELIVERY
add('network', 'Planned DNS record cutover', [
 'The network team handles a planned DNS record cutover by lowering the old record cache lifetime one full old-lifetime interval before the change. The change owner verifies the new destination independently. Editing the destination first and lowering the lifetime afterward cannot shorten caches already issued to clients.',
 'At cutover, the team updates the record and tests resolution through both the company resolver and an external resolver. The old destination stays available through the agreed overlap period. A successful lookup from the operator own laptop is not the only acceptance check.',
 'If rollback is needed, the record can be changed back, but clients may continue using a cached new answer until its lifetime expires. The incident update must acknowledge that delay. The team must not promise that a DNS rollback will reach every client immediately.'
], [
 'When should the network team lower a DNS record cache lifetime before a planned move?',
 'Which resolution checks should confirm a hostname cutover beyond a lookup on the operator laptop?',
 'A DNS cutover is rolled back. Why can some clients continue reaching the new destination for a while?'
])
add('network', 'Public certificate renewal', [
 'The edge team tracks public certificates by hostname, issuer, and expiry date. Renewal begins fourteen days before expiry. The team checks hostname coverage on the replacement certificate before scheduling its installation; having a freshly issued certificate does not guarantee that it covers every served hostname.',
 'After installation, verification is performed against the public endpoint with the intended server name. Checking a certificate file on disk is not enough. The test confirms the served certificate chain, expiry date, and hostname match from outside the edge host.',
 'A newly renewed certificate can be correct while one old edge node still serves its predecessor. The team checks every active edge pool before closing the change. Clearing a browser cache does not repair an inconsistent certificate rollout across serving nodes.'
], [
 'How far before expiry should public certificate renewal begin?',
 'How do we verify that visitors receive the replacement certificate rather than merely confirm that a new file exists?',
 'Some clients still see the previous certificate after renewal. What deployment consistency check is required?'
])
add('network', 'Reverse-proxy latency diagnosis', [
 'The delivery team investigates slow web responses by separating time spent at the reverse proxy from time waiting for the upstream application. It compares request identifiers across proxy timing records and application traces. Total response duration alone cannot identify which part of the path is responsible.',
 'If proxy connection setup is quick but upstream waiting time is high, the case moves to the application owner with the correlated trace. Increasing proxy worker count is not the default remedy. The handoff includes example request identifiers and the time window affected.',
 'A slow upload is assessed using request-body receipt timing before the team blames the application response path. The proxy can spend most of the request waiting for the client to finish sending data. That pattern is treated differently from an application that accepted the request promptly but answered slowly.'
], [
 'Which timings help separate reverse-proxy delay from application delay?',
 'The gateway connects quickly, then waits a long time for the upstream answer. Which team should investigate next?',
 'A client takes a long time to upload a request body. Should that automatically be classified as a slow application response?'
])
add('network', 'Employee VPN connection troubleshooting', [
 'The help desk diagnoses a failed employee VPN connection by checking ordinary internet reachability, the registered device trust state, and the sign-in result. It records the first failing stage. Repeatedly reinstalling the VPN client before identifying that stage can hide useful evidence.',
 'If authentication succeeds but internal names cannot be resolved, the desk inspects the DNS settings delivered inside the tunnel. A successful sign-in does not prove that internal name resolution is correct. The diagnostic record includes an internal hostname and its observed resolver response.',
 'When one employee cannot establish a tunnel but office users can reach the same application, the case remains an employee connectivity problem. It does not trigger a company-wide application incident solely because the employee describes the application as unavailable.'
], [
 'What stages should the help desk check when an employee VPN connection fails?',
 'The remote-access tunnel signs in successfully, but company hostnames do not resolve. What should support inspect?',
 'Only one remote employee cannot connect, while office users can use the application. Is that enough to declare an application-wide outage?'
])
add('network', 'Bastion-mediated server login', [
 'Administrators reach managed servers through the company bastion using a short-lived SSH certificate tied to their employee identity. Direct inbound SSH from personal internet addresses is not part of the managed access path. The bastion records the target host and employee for the session.',
 'When a certificate expires during a long maintenance task, the administrator obtains a new certificate before opening another connection. Copying a private key from a teammate is not an approved workaround. The maintenance change can remain open while the login credential is renewed.',
 'A server that cannot be reached through the bastion is checked for target registration and its internal access rules. The operator must not open public SSH as a quick diagnostic measure. Access failures are repaired inside the managed path instead of creating another entry point.'
], [
 'What is the approved path for administrators to open an SSH session to a managed server?',
 'An administrator short-lived login certificate has expired. How should they open another connection?',
 'A target cannot be reached through the bastion. Should an operator temporarily expose public SSH to diagnose it?'
])
add('network', 'Firewall exception expiry', [
 'A firewall exception request identifies the source, destination, protocol, port, business reason, and an expiration date. The network steward approves the narrowest matching rule. Requests for unrestricted traffic between two networks are returned for a more specific definition.',
 'Temporary exceptions expire after seven days unless the owner obtains a reviewed extension. The rule inventory sends a reminder before removal. A quiet traffic graph does not automatically renew a rule, and an open support ticket is not an approved extension.',
 'If a production connection must continue permanently, the service owner documents it as a standing dependency and submits it for normal network-policy review. The team must not keep renewing a temporary exception indefinitely to avoid recording that dependency.'
], [
 'What fields are needed to request a temporary firewall exception?',
 'Does an unresolved support ticket keep an expiring network rule active beyond its approved period?',
 'A service now needs an ongoing connection that began as a short exception. How should the owner authorize it permanently?'
])
add('network', 'Targeted edge-cache invalidation', [
 'The web team removes stale edge content by invalidating the affected resource paths or cache tags after confirming that the origin serves the new version. An invalidation cannot repair content that is still old at the origin. The request lists the exact resources that need refreshing.',
 'The operator verifies a fresh response from multiple edge locations and records the content version observed. A whole-site purge is reserved for cases where targeted tags cannot cover the affected set. Purging unrelated objects can create an unnecessary load spike at the origin.',
 'Personal browser storage is separate from the shared edge cache. If only one browser shows old content while clean clients receive the new version, the team investigates that browser state. Repeatedly invalidating the shared cache is not the first response to a single-client symptom.'
], [
 'What must be checked at the origin before requesting an edge-cache invalidation?',
 'Why should the web team prefer refreshing selected cache tags over clearing the whole site?',
 'Only one browser shows old content while clean clients are current. Should the team keep purging the shared edge cache?'
])
add('network', 'Webhook retry rate control', [
 'Aster Works receivers signal temporary request throttling with a retry interval. Integration clients honor that interval and add jitter before another attempt. Retrying immediately from every worker can synchronize traffic and prolong the overload that caused the throttle.',
 'Clients retain the original delivery identifier across retries so the receiver can recognize repeated delivery of the same event. Generating a new identifier for each attempt defeats the receiver duplicate check. The retry count is recorded separately from the event identity.',
 'A permanent validation rejection is not placed on the temporary-throttle retry loop. The sender stores the rejected event and its explanation for correction. Waiting longer will not make a malformed required field valid, so repeated timed retries only add noise.'
], [
 'How should webhook clients respond to a temporary throttling response?',
 'Should repeated attempts to deliver one event use new identifiers or retain the original identity?',
 'A receiver rejected an event because a required field is invalid. Does the temporary-throttle retry policy apply?'
])
add('network', 'Load-balancer connection draining', [
 'Before stopping an application node, the release operator marks it unavailable for new load-balanced requests. Existing connections are allowed to finish within the drain window. Killing the process before draining can interrupt requests that were already accepted.',
 'The drain window is ninety seconds. The operator watches the active connection count and stops the node once connections finish or the approved limit is reached. A node disappearing from new-request rotation does not prove that every old connection is already gone.',
 'Long-running streaming endpoints need a service-specific shutdown plan because their connections may outlive the standard drain window. The release owner checks that plan before maintenance. Extending every node drain indefinitely is not a substitute for defining how streaming clients reconnect.'
], [
 'What should a release operator do before stopping a node behind a load balancer?',
 'A node no longer receives fresh traffic. How can the operator determine whether accepted requests still need time to finish?',
 'A streaming connection can last longer than the normal ninety-second drain. What must the service owner prepare?'
])
add('network', 'Canary deployment traffic promotion', [
 'A canary release sends five percent of eligible requests to the new application version while the old version remains available. The release operator checks error rate and response latency against the old-version control. A healthy process startup alone is not evidence that live requests are behaving correctly.',
 'Promotion beyond the canary share requires fifteen minutes within the agreed error and latency bounds. The release log records the comparison window and the version identifiers. Low request volume can require a longer observation period rather than an automatic pass after the clock expires.',
 'If the canary misbehaves, the operator first returns its traffic share to zero while retaining its logs for diagnosis. This action is distinct from changing DNS or draining every node. The control version continues serving traffic during the canary rollback.'
], [
 'What traffic share starts a canary release, and what is compared against the control?',
 'Does a new version become eligible for promotion merely because its process is healthy and fifteen minutes have elapsed?',
 'A canary causes errors while the old version is healthy. What traffic action should happen before broader rollback measures?'
])

# INCIDENT MANAGEMENT
add('incidents', 'Incident priority assignment', [
 'The duty responder assigns incident priority from current customer impact, the number of affected workspaces, and the availability of a usable workaround. The report urgency label is only an input. A request from a senior employee does not by itself make a case the highest priority.',
 'A widespread inability to perform a core paid workflow is priority one when no practical workaround exists. A cosmetic problem with an available alternative usually receives a lower priority. The responder records observed impact so later reviewers can understand the decision.',
 'Priority is reassessed when evidence changes. A case initially limited to one workspace can be raised when the same failure is confirmed across many workspaces. The original classification remains in the timeline rather than being silently overwritten as though the broader impact was known from the start.'
], [
 'What evidence determines an incident priority at initial triage?',
 'When does a failure of a paid workflow qualify for the most urgent response level?',
 'An issue thought to affect one workspace is now confirmed in many workspaces. What should happen to its priority and history?'
])
add('incidents', 'Incident timeline recording', [
 'The incident scribe keeps a chronological record of observations, decisions, and actions using UTC timestamps. Each entry distinguishes an observed fact from a working hypothesis. A useful timeline makes it possible to reconstruct what responders knew at each decision point.',
 'Corrections are added as new entries that refer to the earlier statement. The scribe does not erase an incorrect early hypothesis after a better explanation appears. Preserving that transition helps the review explain why an action seemed reasonable at the time.',
 'The timeline is an operational record rather than the customer-facing status message. Internal hostnames and detailed diagnostic assumptions may belong in the timeline but not in a public update. The communications owner prepares a separate message from verified customer impact.'
], [
 'What should an incident scribe record, and which timestamp convention is used?',
 'How should an early incident assumption be corrected after responders discover it was wrong?',
 'Can the internal responder timeline be copied directly into a customer-facing status update?'
])
add('incidents', 'Customer incident status updates', [
 'The communications owner publishes a customer incident update after the incident commander confirms the affected workflow and scope. The message describes user-visible impact and the next expected update time. It avoids presenting an untested internal theory as an established cause.',
 'An active priority-one incident receives a public progress update at least every thirty minutes, even if the technical investigation has not reached a new conclusion. The owner can say that work continues and repeat the known impact. Silence is not used to avoid admitting uncertainty.',
 'A resolved update is published after the team verifies service recovery from a customer perspective. A restarted process alone is not enough to declare resolution. The message separates restored service from any remaining work to investigate the underlying cause.'
], [
 'What information belongs in the first customer-facing incident update?',
 'Should customers receive another update if a severe incident investigation has found nothing new for half an hour?',
 'An application process restarted successfully. Is that sufficient evidence to publish that the customer incident is resolved?'
])
add('incidents', 'Production change rollback decision', [
 'The incident commander can request rollback when a recent production change is strongly associated with the observed failure and the previous state is known to be recoverable. The release owner identifies the affected version and checks the rollback plan before executing the reversal.',
 'Changes with irreversible data transformations require a recovery decision with the data owner. Deploying the old binary alone may not restore compatibility with the changed records. The responder checks the data migration state rather than assuming that every release can be reversed in the same way.',
 'After rollback, the team verifies the failed customer workflow and watches for delayed side effects. The action is recorded in the incident timeline with its outcome. A successful deployment command is not proof that the reversal fixed the original failure.'
], [
 'What should be checked before an incident-driven production rollback?',
 'Why might redeploying an old program version fail to undo a release that transformed stored data?',
 'The rollback command completed without error. What must responders verify before treating the original problem as repaired?'
])
add('incidents', 'Post-incident learning review', [
 'A learning review is scheduled within five working days after a significant incident closes. The review owner assembles the timeline, customer impact, contributing conditions, and recovery actions. The purpose is to understand the system and improve response rather than assign personal blame.',
 'Every agreed improvement receives an owner, a measurable completion condition, and a target date. A vague instruction to be more careful is not accepted as a corrective action. The review links each action to the condition it is meant to change.',
 'The review may take place before the team has proved one final root cause. It records remaining uncertainty and assigns follow-up investigation where useful. Waiting indefinitely for a perfect explanation is not a reason to miss the scheduled learning opportunity.'
], [
 'When should a post-incident learning review take place?',
 'What makes a follow-up improvement actionable rather than a general promise to be more careful?',
 'The team has restored service but still has competing explanations. Must the learning review wait until one cause is proved?'
])
add('incidents', 'Exposed-secret containment', [
 'A credential found in a public repository or external message is treated as exposed even if nobody has reported misuse. The owning team revokes it immediately and arranges a replacement. Removing the visible text does not make the old credential trustworthy again.',
 'Responders inspect authentication records for the exposure window and preserve the evidence in the restricted incident record. They record the secret identifier rather than paste the live value into an ordinary chat. Any suspicious use is investigated under the same containment case.',
 'A leaked credential does not follow the one-day overlap allowed for ordinary API-key rotation. Integrations may need a coordinated emergency replacement, but the exposed key is not left valid for convenience. The incident commander accepts the resulting service tradeoff explicitly.'
], [
 'What is the first credential action after a secret appears in a public repository?',
 'After disabling a published credential, how should responders investigate whether someone used it?',
 'Can an exposed integration key stay active for the routine rotation overlap while consumers migrate?'
])
add('incidents', 'Message-queue backlog response', [
 'The messaging responder compares incoming event rate, successful processing rate, oldest-message age, and consumer failures when a queue grows. Queue length alone does not identify the cause. A large queue may be draining normally after a temporary burst, while a smaller queue can contain very old blocked work.',
 'If consumers repeatedly fail on one event, the responder moves that event to the quarantine path with its original payload and error history. The team then allows other events to proceed. Deleting every pending message is not an acceptable way to make the queue-depth graph look healthy.',
 'Adding more consumers is considered only when the downstream service can tolerate additional concurrency. A saturated dependency can become less stable when retries and workers are multiplied. The owner checks dependency capacity before approving a scale-out action.'
], [
 'Which measurements should be compared when investigating a growing message queue?',
 'One repeatedly failing event is holding up useful queued work. How should responders handle that event?',
 'The queue is growing because its downstream database is already saturated. Should the responder immediately add more consumers?'
])
add('incidents', 'Payment-provider incident isolation', [
 'When checkout fails, the payments responder separates local application errors from payment-provider timeouts and rejection responses. The team uses correlation identifiers to follow requests across the boundary. A declined card and an unavailable provider are different incident patterns.',
 'If the provider accepted a payment but the local confirmation is missing, the responder queries the provider by the original transaction reference before retrying the charge. Repeating the charge with a new reference can create a duplicate payment rather than repair the missing local confirmation.',
 'A provider-wide outage is communicated as a checkout availability issue while unrelated account features remain available. The team does not disable every customer account because payments are delayed. Recovery checks include reconciling pending transaction references once the provider responds again.'
], [
 'What distinctions help isolate a checkout incident to the payment provider?',
 'A customer payment may have succeeded externally while our confirmation timed out. What should happen before another charge attempt?',
 'The payment provider is unavailable but other account features work. Should all customer accounts be disabled?'
])
add('incidents', 'Restricted data-exposure handoff', [
 'A responder who suspects unintended access to customer data opens a restricted incident record and notifies the privacy duty lead. The record contains the affected system, suspected time window, and the evidence location. Detailed customer records are not copied into the general incident channel.',
 'The privacy duty lead coordinates scope assessment and determines which additional specialists should participate. The first responder preserves the original access records and avoids changing them during investigation. An absence of confirmed harm does not justify discarding evidence of possible access.',
 'Decisions about notifying affected customers are made through the restricted response group after scope assessment. An individual engineer must not independently contact customers based on an unverified early hypothesis. Ordinary service-status messages remain separate from that decision process.'
], [
 'Where should a responder report suspected unintended customer-data access?',
 'What should happen to original access records while a possible data exposure is being assessed?',
 'An engineer suspects customer information was exposed but scope is unverified. Who decides whether affected customers are contacted?'
])
add('incidents', 'Scheduled maintenance notice', [
 'The service owner announces planned customer-visible maintenance at least three working days in advance. The notice gives the affected feature, start time, expected duration, and any customer preparation. Scheduling the work does not remove the need to describe its user-visible effects.',
 'If maintenance runs beyond its published end time, the communications owner posts an extension with the current impact and another update time. The original notice remains visible so users can see that the window changed. Quietly editing the original end time is not sufficient communication.',
 'An unexpected failure during maintenance is handled as an incident when its impact exceeds the approved maintenance scope. The team does not hide an unrelated severe outage inside an existing maintenance banner. Incident priority is assigned from the actual customer impact.'
], [
 'How far in advance should customer-visible maintenance be announced?',
 'What communication is required when planned maintenance lasts longer than its advertised window?',
 'An unrelated severe outage begins during a small scheduled change. Should it remain classified only as planned maintenance?'
])

# KNOWLEDGE AND DOCUMENT MANAGEMENT
add('knowledge', 'Publishing a knowledge article', [
 'An author submits a new knowledge article with a descriptive title, an accountable owner, a source location, and a review date. The knowledge editor checks that the content can stand on its own. A link with no explanation is not accepted as a complete article.',
 'Publication makes the approved text eligible for indexing, but indexing completion is recorded separately. Authors can inspect the indexing state before promising that a new article will appear in semantic search. A published page is not necessarily searchable immediately.',
 'If an existing article already answers the same question for the same audience, the editor asks for an update to that article instead of another independent copy. A new title alone does not make duplicate instructions a distinct knowledge entry.'
], [
 'What ownership and source information is needed to publish a knowledge article?',
 'A page is visible in the editor but cannot yet be found by semantic search. Which separate state should the author inspect?',
 'An author proposes another article with the same instructions for the same audience. Should the editor publish it as a separate entry?'
])
add('knowledge', 'Knowledge taxonomy assignment', [
 'The knowledge editor assigns each article a primary service category and an audience label from the shared taxonomy. Authors can propose additional descriptive tags, but primary categories use the controlled list. Inventing a near-duplicate spelling makes category-based browsing less reliable.',
 'A new primary category requires approval from the taxonomy steward with examples of articles that existing categories cannot represent. One author preference is not enough to expand the list. The steward checks the effect on existing navigation before approving another category.',
 'Changing an article category updates browsing and filtering metadata without rewriting its body. The editor verifies any saved category-based views after the change. Reclassifying a page is different from replacing its content or creating another article identity.'
], [
 'Which article metadata fields must use the controlled knowledge taxonomy?',
 'How can an author justify adding a new primary browsing category?',
 'A page needs to move to a different category while its instructions stay valid. Does that require a new article identity?'
])
add('knowledge', 'Retiring obsolete instructions', [
 'An article owner retires instructions when the described process is no longer valid. Retirement removes the entry from normal search and navigation but keeps its historical record. The owner records the reason and, when available, a replacement article.',
 'Old links to a retired article show a retirement notice and the approved replacement rather than silently presenting outdated instructions as current. This behavior helps readers understand why a saved bookmark no longer leads to an active procedure.',
 'Retirement is different from permanent deletion of sensitive content. If the text must be removed for a restricted-data reason, the owner opens a controlled removal request. Ordinary retirement preserves history and therefore cannot be used to guarantee that every historical copy has disappeared.'
], [
 'What happens to an obsolete knowledge article when its owner retires it?',
 'How should readers following old bookmarks be directed when a procedure has been replaced?',
 'A page contains content that must be permanently removed from history. Is normal article retirement sufficient?'
])
add('knowledge', 'Merging duplicate knowledge pages', [
 'When two active articles repeat the same procedure, the editor selects a canonical page and compares both versions for unique information. Useful material is incorporated into the canonical page before the duplicate is retired. Choosing the newer page automatically can discard details that only the older version contains.',
 'The duplicate page retains a redirect notice to the canonical article, and its former owner is recorded in the merge history. Search indexing is refreshed so the duplicate no longer competes with the chosen page. The canonical page keeps its own stable identifier.',
 'Pages that discuss similar tools but prescribe different actions are not duplicates merely because their titles overlap. The editor compares purpose, audience, and decision conditions. A guide for routine key rotation and a leaked-secret containment procedure must remain separate despite shared vocabulary.'
], [
 'What should an editor compare before merging two duplicate knowledge pages?',
 'How do old links and search results change after duplicate instructions are consolidated?',
 'Two guides mention API credentials, but one covers routine rotation and the other emergency exposure. Should similar wording make them a merge candidate?'
])
add('knowledge', 'Search permission synchronization', [
 'The knowledge service copies source access rules into its searchable document permissions. A reader may receive a result only if their current identity can view the source. Being able to guess the title or source identifier does not provide access to the indexed text.',
 'When an article access rule changes, the permission synchronization job updates the search authorization state separately from content embedding. The owner checks the permission job completion marker. Rebuilding vector embeddings is not by itself evidence that a removed viewer can no longer receive the article.',
 'An indexing operator who sees a permission synchronization failure suspends the affected document from serving until its access state is trustworthy. The operator does not make the article public just to clear a failed job. Content visibility remains narrower than operational access to the indexing system.'
], [
 'What authorization check determines whether a reader may receive a knowledge search result?',
 'A viewer was removed at the source. Which synchronization state should be checked rather than simply rebuilding the vectors?',
 'The service cannot synchronize an article access rules. Should an operator make it public so indexing can finish?'
])
add('knowledge', 'Stale-article review reminders', [
 'The knowledge service sends an owner reminder when an active article reaches its review date. The owner checks whether the instructions still match the process and either confirms them or submits a revision. Opening the reminder does not count as completing that review.',
 'Confirmation records a new review date and the person who verified the instructions. A spelling correction alone is not considered confirmation that the operational guidance remains valid. The review record states what process or owner was consulted.',
 'An article with no reachable owner is routed to the service steward for reassignment. The review date is not repeatedly pushed forward to hide the ownership gap. If nobody can establish that the instructions are still safe to follow, the steward can retire the article.'
], [
 'What should an owner do when a knowledge article reaches its review date?',
 'Does fixing a typo establish that old operating instructions have been checked for current validity?',
 'A stale article has no reachable owner. Who should resolve its ownership rather than just postpone its review date?'
])
add('knowledge', 'Investigating a poor semantic result', [
 'A reader reports an unhelpful search result with the exact query, the returned article, and the article they expected instead. The search steward reproduces the case using the same access permissions. A report that only says search is bad does not identify a testable retrieval failure.',
 'The steward first checks whether the expected source was indexed and visible to that reader. If it is absent or unauthorized, changing embedding settings cannot make it an eligible answer. Retrieval-quality investigation begins only after source presence and permissions are confirmed.',
 'Once eligibility is established, the steward examines chunk boundaries, source wording, and query representation. A model change is evaluated against a frozen set of labeled queries rather than just the one complaint. A single successful demonstration is not a sufficient regression test for replacing the model.'
], [
 'What evidence should a reader provide when reporting an unhelpful semantic search result?',
 'Why should the search steward confirm that an expected page is indexed and authorized before changing the embedding model?',
 'One complaint improves after a model switch. What broader evidence is required before replacing the retrieval model?'
])
add('knowledge', 'Source attachment replacement', [
 'An article owner replaces an attached source file by creating a new source revision under the existing article identity. The knowledge service records the original filename and revision reference. Uploading a changed file with a different arbitrary article title is not the approved replacement workflow.',
 'The new source revision is extracted and indexed before it becomes the active searchable revision. If extraction fails, the previously active revision remains searchable with its existing state. A failed replacement must not silently remove the last valid indexed source.',
 'After the replacement becomes active, the owner checks quoted passages and page references used in the article. Pagination can change even when the attachment filename stays the same. The old revision is retained for traceability rather than edited in place to resemble the new upload.'
], [
 'How should an owner replace an article attached source file while preserving its identity?',
 'A new attachment revision cannot be extracted. What should readers continue receiving until a valid replacement is ready?',
 'A revised source file keeps its old filename but changes pagination. What references must the owner recheck?'
])
add('knowledge', 'Document ingestion format checks', [
 'The ingestion service accepts plain-text files, text-based PDF files, and office documents with extractable text. It checks the declared format against the actual file contents before extraction. Renaming a binary file with a text extension does not make it an accepted input.',
 'A scanned PDF with no embedded text is sent to the document-preparation queue for optical character recognition. It is not indexed as an empty successful article. The preparation result must be checked for readable text before ordinary extraction and chunking continue.',
 'An encrypted or password-protected attachment remains in a blocked ingestion state until the owner supplies an approved readable version. The service does not store the document password in article metadata as a workaround. The readable replacement follows the normal source revision process.'
], [
 'Which kinds of documents can the ingestion service extract and index?',
 'What should happen to an uploaded PDF that contains only scanned page images?',
 'A protected attachment cannot be read. Should its password be added to article metadata so indexing can proceed?'
])
add('knowledge', 'Checking answer citations against sources', [
 'A reviewer checking an answer opens each cited passage and verifies that it supports the associated claim. A relevant article title alone is not sufficient support. The review distinguishes text that explicitly establishes a fact from text that merely discusses the same topic.',
 'If a cited source has been replaced, the reviewer follows the recorded source revision rather than assume that the newest page contains the quoted wording. The answer record must identify which revision supplied the passage. Citation traceability matters even when the new version is broadly similar.',
 'An answer can retrieve useful documents but still state a conclusion that none of them supports. The reviewer marks that as an answer-grounding problem, separate from finding the right source. Improving retrieval alone does not automatically correct unsupported reasoning in the generated answer.'
], [
 'What should a reviewer verify when checking whether a citation supports an answer?',
 'A source changed after an answer was produced. Which version should be used to check its quoted passage?',
 'The correct article was retrieved, but the answer makes an unsupported conclusion. Is that solely a retrieval-ranking failure?'
])

# CUSTOMER BILLING AND SUBSCRIPTIONS
add('billing', 'Customer-requested subscription refund', [
 'Customer support opens a refund request when a subscriber asks to return a paid subscription purchase. The case records the invoice, the reason, and whether service has been used. Support checks the published plan-specific refund rule rather than promise that every cancellation produces money back.',
 'An approved refund is sent to the original payment method and linked to its original transaction. Support tells the customer that processing completion and bank posting are separate events. A completed internal approval does not prove that the funds already appear on the customer statement.',
 'A customer who reports paying twice for one intended purchase is routed to duplicate-charge reconciliation first. That workflow establishes whether a second captured charge exists. Treating an unexplained second charge as a discretionary subscription refund can obscure the actual payment error.'
], [
 'What information should support collect for a customer-requested subscription refund?',
 'A refund has been approved internally. Does that mean the returned money must already be visible on the customer bank statement?',
 'A subscriber says the same purchase was charged twice. Which check should happen before a discretionary refund decision?'
])
add('billing', 'Failed subscription renewal follow-up', [
 'A failed renewal creates a payment-recovery case linked to the subscription and the failed attempt. The billing team checks whether the failure was a temporary provider issue or a customer payment-method problem. It does not create another subscription to retry the same renewal.',
 'The customer receives a secure link to update the payment method during the five-day grace period. Ordinary workspace data stays intact during that period. Support must not request a full card number in chat or store it in the case notes.',
 'If the renewal succeeds during the grace period, the billing team closes the recovery case against the successful attempt reference. If the grace period ends without payment, the subscription enters its documented restricted state. Reopening a support message does not reset that deadline.'
], [
 'What case should be created after an existing subscription fails to renew?',
 'How should a customer replace an unusable payment method while their renewal is in its grace period?',
 'A renewal remains unpaid after the grace period, but support is still talking to the customer. Does that conversation reset the restriction deadline?'
])
add('billing', 'Duplicate-charge reconciliation', [
 'The payments team investigates a suspected duplicate by comparing the original order reference with provider authorization and capture records. Two authorization holds do not necessarily mean two captured payments. The team establishes the actual settled transactions before deciding what correction is needed.',
 'If two captures exist for one intended order, the team reverses the excess capture and links the correction to both provider references. It preserves the valid purchase and its service entitlement. Canceling the entire subscription is not the default repair for one duplicated payment.',
 'If the second visible item is only an authorization hold, support explains that distinction and records the provider hold reference. The team must not issue an extra refund for funds that were never captured. The case remains auditable even when no captured duplicate is found.'
], [
 'How does the payments team determine whether a customer really paid twice?',
 'Two settled charges are confirmed for one intended order. How should the excess be corrected without canceling the valid purchase?',
 'A bank statement shows a second pending hold but no second capture. Should support refund that hold as though it were a settled payment?'
])
add('billing', 'Mid-term annual plan upgrade', [
 'An existing annual subscriber can request a move to a higher plan during the term. The billing service calculates the remaining-period adjustment and presents it for acceptance before changing the entitlement. A support agent must not guess the adjustment from the full annual list prices.',
 'The original renewal anniversary remains unchanged after a mid-term upgrade. The higher entitlement starts when the upgrade payment succeeds, not when the quote is merely viewed. The adjustment covers the remaining portion of the existing term rather than starting another full year.',
 'If an upgrade quote expires before acceptance, the customer receives a newly calculated quote. Support does not reuse an old adjustment amount after the remaining term has changed materially. Quotation and completed entitlement change remain separate states in the account history.'
], [
 'How is the charge for an annual subscription upgrade determined partway through the term?',
 'Does moving to a higher annual plan create a new renewal anniversary or preserve the original date?',
 'A customer wants to accept an expired upgrade quote. Should support apply its old adjustment amount unchanged?'
])
add('billing', 'Issued invoice detail correction', [
 'The billing desk checks a requested invoice correction against the customer billing profile and the original issued document. The case identifies the exact field that is wrong. Editing the customer profile alone does not rewrite an invoice that has already been issued.',
 'For an issued invoice, the billing team produces the approved correcting document and links it to the original record. The original issued version remains preserved. Support must not replace the old downloadable file silently as though the corrected text had always been issued.',
 'A request to change the recipient on future invoices is a billing-profile update rather than a correction of all historical invoices. The team confirms the effective date of the profile change. Old documents are corrected only through their own explicit requests.'
], [
 'What should a customer identify when requesting a correction to an issued invoice?',
 'Can support silently overwrite an issued invoice file after fixing its details?',
 'A customer changes the recipient details for future billing. Does that automatically rewrite every historical invoice?'
])
add('billing', 'Trial period extension review', [
 'The account owner can request a one-time extension of an active trial when the customer could not complete a planned evaluation. The request records the evaluation task and why the original period was insufficient. A trial extension does not create a paid subscription.',
 'An approved extension adds seven days to the existing trial end date. Support records the approving account owner and notifies the customer of the new deadline. Changing a reminder email does not change the underlying trial entitlement.',
 'An account that has already converted to a paid plan does not return to trial through this process. Any commercial adjustment for that account follows the paid-subscription workflow. The trial tool must not be used to bypass a billing correction or refund decision.'
], [
 'Who can request an extension when a customer needs more time for an active trial?',
 'What changes when a one-time trial extension is approved?',
 'A customer has already become a paying subscriber. Can support use the trial-extension tool to turn the account back into a trial?'
])
add('billing', 'Workspace usage-quota adjustment', [
 'A workspace owner requests a usage-quota adjustment with the affected meter, the desired limit, and the expected duration. The service owner checks capacity and the account entitlement before approval. Increasing one meter does not automatically raise every limit on the workspace.',
 'A temporary quota increase carries an expiry time and a notification plan for the workspace owner. The account returns to its approved standing limit at expiry. A successful test during the temporary period does not make the higher quota permanent.',
 'If the account needs a lasting allowance that exceeds the current plan, the account team reviews a plan change rather than continually renew a temporary override. The quota record distinguishes a capacity exception from a commercial entitlement change.'
], [
 'What information is needed to request a workspace usage-quota increase?',
 'Will a temporary allowance remain permanent merely because the customer successfully used it?',
 'A workspace repeatedly needs more capacity than its plan allows. Should support keep extending a short quota exception indefinitely?'
])
add('billing', 'Billing currency change request', [
 'The billing team reviews a request to change the currency of future subscription charges at the next renewal boundary. The account owner confirms the requested currency before a new renewal quote is accepted. Existing settled transactions retain the currency in which they were processed.',
 'The new quote uses the approved pricing schedule for the requested currency rather than a support agent manual conversion of an old invoice total. The customer accepts the quote before the future billing currency is updated. Historical charge amounts are not recalculated by this operation.',
 'A request concerning an incorrect amount on an already-issued invoice is routed to invoice correction instead. Changing the future billing currency does not repair a historical invoicing error. The two cases can be linked while retaining their different effective dates.'
], [
 'When can a requested subscription billing currency change take effect?',
 'How is the future price established when a customer moves to another billing currency?',
 'An existing invoice has the wrong amount. Will changing the currency used at the next renewal correct that document?'
])
add('billing', 'Payment dispute evidence package', [
 'A provider payment dispute opens a restricted case owned by the payments team. The team records the provider deadline and collects the order reference, customer agreement, and evidence of service delivery. A general customer-support note is not a complete dispute response.',
 'The response package is reviewed before submission through the provider dispute channel. The team records the submitted package identifier and submission time. Sending an ordinary email to the customer does not satisfy a provider evidence deadline.',
 'While a dispute is open, support coordinates any proposed refund with the payments owner. An independent refund can overlap with the provider reversal and return the same amount twice. The dispute state must be checked before another corrective payment is initiated.'
], [
 'What evidence should the payments team gather for a provider payment dispute?',
 'Does emailing a customer satisfy the deadline for submitting evidence to a payment provider?',
 'A disputed payment is under provider review and support wants to refund it. Why must the payments owner be consulted first?'
])
add('billing', 'Goodwill account-credit approval', [
 'The account team can propose a goodwill credit for a documented service problem without changing the original invoice correctness. The proposal states the reason, amount, and affected account. Goodwill credit is a commercial accommodation rather than proof that a historical charge was invalid.',
 'Credits above two hundred internal billing units require approval from the duty finance manager. Smaller proposals still need an account owner approval and a recorded reason. Splitting one proposed accommodation into smaller credits does not remove the higher approval requirement.',
 'An approved credit is applied to future eligible invoices and is not automatically sent back to the original payment method. A customer who specifically needs money returned requires a refund review. The credit note and the refund transaction are different outcomes.'
], [
 'What information supports a goodwill account-credit proposal?',
 'Can one large accommodation be divided into small credits to avoid the finance-manager approval threshold?',
 'Does approving account credit automatically return cash to the customer original payment method?'
])

# WAREHOUSE AND FULFILLMENT
add('logistics', 'Registering a new warehouse item', [
 'The inventory coordinator registers a new item before the warehouse receives its first stock. The record includes the supplier reference, unit of measure, storage requirements, and a unique stock code. A supplier description alone is not used as the permanent item identifier.',
 'If one supplier changes the packaging quantity, the coordinator checks whether the unit of measure has changed before reusing the old item record. Receiving a carton as though it were one individual unit can distort stock counts even when the product description looks unchanged.',
 'An existing item from another supplier normally keeps its internal stock identity when the physical specification is equivalent. The coordinator adds the alternative supplier reference after review. A new supplier name alone does not require another independent stock code.'
], [
 'Which fields must be registered before a warehouse item first arrives?',
 'A supplier changes how many pieces are in each carton. What should inventory staff check before receiving stock?',
 'An equivalent item is now purchased from a different supplier. Does the supplier name alone require a new stock identity?'
])
add('logistics', 'Investigating an inventory quantity adjustment', [
 'A warehouse supervisor reviews a proposed inventory adjustment against a physical recount and the recent movement history. The request records the observed quantity, recorded quantity, and likely reason for the difference. An unexplained spreadsheet change is not an approved stock correction.',
 'The adjustment record preserves the previous balance and the counted evidence. A correction does not erase the movements that produced the old balance. This history lets a later reviewer distinguish a counting error from a missed receipt or dispatch.',
 'If the discrepancy is caused by a receipt that was never posted, staff correct the missing receipt workflow rather than add a second unrelated quantity adjustment. The underlying movement should be represented once. A convenient numerical fix must not create duplicate stock later.'
], [
 'What evidence should support a proposed warehouse inventory quantity adjustment?',
 'Does correcting the stock balance remove the historical movements that led to the old number?',
 'A stock mismatch comes from an unposted delivery receipt. Should the warehouse add an unrelated adjustment before posting that receipt?'
])
add('logistics', 'Receiving damaged supplier goods', [
 'Receiving staff separate visibly damaged incoming goods from saleable stock before completing the receipt. They record the supplier, delivery reference, affected quantity, and photographs of the damage. Damaged units must not be made available for customer picking simply because the delivery arrived on time.',
 'The supplier coordinator requests a replacement, credit, or approved disposal decision using the damage record. The warehouse holds the units in a quarantine location while that decision is pending. Moving them to quarantine does not by itself complete a supplier credit agreement.',
 'Damage found at incoming receipt is treated as a supplier-delivery case rather than a customer return. The two workflows use different ownership and evidence. Staff must not create a fictional customer order merely to move damaged received goods through a returns screen.'
], [
 'What should receiving staff do with supplier goods that arrive visibly damaged?',
 'Does placing damaged incoming stock in quarantine mean the supplier has already agreed to compensate the company?',
 'No customer bought the damaged units; they arrived that way from a supplier. Which intake workflow should handle them?'
])
add('logistics', 'Tracing a missing outgoing parcel', [
 'The dispatch desk investigates a missing outgoing parcel using the customer order, carrier tracking reference, handoff scan, and last confirmed movement. A label being printed is not proof that the carrier received the package. The handoff evidence determines which part of the route needs investigation.',
 'If the carrier confirms loss after handoff, the order owner chooses an approved replacement shipment or customer refund. The replacement retains a link to the original parcel case. Creating an unlinked new order can hide whether the customer received one or two remedies.',
 'If no handoff scan exists, the warehouse searches its dispatch area before opening a carrier-loss claim. A package still inside the building cannot be located by asking the carrier to trace it. The case remains a warehouse dispatch investigation until custody transfer is established.'
], [
 'What evidence helps establish where an outgoing parcel went missing?',
 'The carrier confirms that it lost a dispatched package. How should the customer remedy be linked to the original case?',
 'A label exists, but there is no carrier handoff scan. Should the desk begin by claiming carrier loss?'
])
add('logistics', 'Preparing a cross-border shipment', [
 'The export coordinator checks the destination, item classification, declared value, and required shipping documents before approving a cross-border parcel. The carrier label is only one document in that check. A parcel is not released merely because a domestic dispatch screen accepted its address.',
 'Declared descriptions must identify the actual goods and their quantities. A vague description such as miscellaneous items is returned to the order owner for clarification. The coordinator uses the approved product information rather than inventing a description to make the form submit.',
 'If a customer changes the destination country after documents are prepared, the shipment returns to export review. The team does not simply edit the street label while retaining paperwork for the previous country. Destination changes can affect the required preparation even when the ordered item is unchanged.'
], [
 'What should the export coordinator check before releasing a cross-border parcel?',
 'How should shipping staff handle a declaration that only describes its contents as miscellaneous items?',
 'The destination country changes after export paperwork is prepared. Can staff update only the address label?'
])
add('logistics', 'Inspecting a customer product return', [
 'Returns staff receive customer goods against an approved return reference and compare the item and quantity with that authorization. They record condition separately from the customer stated reason. An unopened package is not automatically returned to saleable stock without the required inspection.',
 'Inspection determines whether the goods are restockable, repairable, or unsuitable for reuse. The outcome is sent to the order owner for the customer remedy decision. Warehouse inspection does not itself authorize a payment refund outside the billing workflow.',
 'A returned parcel with no valid reference is held in an unidentified-return location while support locates its owner. Staff do not attach it to the first vaguely similar order. Preserving that distinction avoids giving a remedy to one customer for another customer returned item.'
], [
 'What should the warehouse compare when receiving an authorized customer return?',
 'Does a warehouse decision that returned goods cannot be reused automatically authorize a payment refund?',
 'A parcel arrives without a recognizable return reference. Should staff assign it to a roughly similar customer order?'
])
add('logistics', 'Cold-storage temperature excursion', [
 'A cold-storage alarm creates a temperature-excursion record with the affected zone, time range, observed readings, and stock locations. Staff isolate potentially affected lots while the quality owner assesses them. A current normal reading does not prove that an earlier excursion caused no problem.',
 'The quality owner compares the recorded exposure with the item handling specification and decides whether each lot can be released. Warehouse staff cannot clear the hold simply because an outgoing order is urgent. The release decision is attached to the individual lot record.',
 'If only one storage zone was affected, staff trace actual lot locations during the event instead of quarantining unrelated stock by product name alone. Movement history matters because a lot may have entered or left the zone during the excursion window.'
], [
 'What information belongs in a cold-storage temperature-excursion record?',
 'Can an urgent customer order override the quality hold on stock exposed to an abnormal temperature?',
 'Only one cold-storage zone overheated. How should staff identify which lots were actually exposed during the event?'
])
add('logistics', 'Blind inventory cycle counting', [
 'The inventory team schedules a cycle count for selected storage bins and temporarily pauses movements in those bins. Counters receive item identities but not the expected system quantities. This blind method helps prevent the recorded number from influencing the physical count.',
 'A variance above the review threshold triggers a second count by another person before an adjustment is proposed. The original count is preserved. Replacing the first count with the expected balance would hide whether there was a counting mistake or a genuine stock discrepancy.',
 'If a movement occurred while a supposedly frozen bin was being counted, the supervisor reconciles that movement and repeats the affected count. The count is not treated as a clean snapshot of one moment when stock changed during the observation window.'
], [
 'Why are expected stock quantities hidden during a blind cycle count?',
 'What should happen before a large difference from the expected inventory balance becomes an adjustment?',
 'Goods moved through a bin while its count was underway. Can that count be accepted as an unchanged snapshot?'
])
add('logistics', 'Partial fulfillment and split dispatch', [
 'An order owner can approve split dispatch when some items are ready and the remaining items have a later availability date. The customer is informed which lines will leave first. The order remains one commercial purchase with multiple linked shipments, not several unrelated purchases.',
 'Each shipment carries its own tracking reference and the quantities actually dispatched. The remaining balance stays open against the original order. Marking the whole order delivered when only the first parcel arrives would conceal the outstanding goods.',
 'If the customer declines a split, the warehouse holds the ready lines for the agreed consolidation window. Staff do not send them anyway because labels were already printed. The dispatch decision follows the recorded customer arrangement rather than the convenience of an existing picking batch.'
], [
 'How is an approved split dispatch represented against the customer purchase?',
 'The first parcel of a split order has arrived. Should the entire order be marked delivered?',
 'The customer asked for one consolidated delivery, but labels for available items are ready. Can the warehouse send those items separately?'
])
add('logistics', 'Preorder stock release', [
 'A preorder becomes eligible for fulfillment when its expected stock is received, inspected, and allocated to the waiting order. A supplier promise of arrival is not a warehouse release signal. The order owner confirms that the actual item specification matches the preorder before allocation.',
 'Waiting orders are allocated according to the recorded reservation sequence unless an approved exception explains a different order. Staff do not assign all arriving stock to the most recent request simply because it is visible at the top of a screen.',
 'If the received item is a substitute rather than the originally reserved specification, the account owner obtains customer acceptance before releasing it. The warehouse must not treat a similar product name as permission to fulfill a preorder with materially different goods.'
], [
 'What events make a preorder eligible for warehouse fulfillment?',
 'How should newly received stock be allocated among customers who have been waiting for a preorder?',
 'A similar replacement product arrives instead of the reserved specification. Can it be dispatched to preorder customers without acceptance?'
])

# ANALYTICS AND DATA OPERATIONS
add('data', 'Registering a new analytics feed', [
 'A data producer registers a new analytics feed with its owner, event purpose, schema, and expected delivery frequency. The data platform team checks the contract before enabling production ingestion. A sample file arriving in storage does not automatically create a supported analytics source.',
 'The first delivery is validated in a staging dataset for required fields, event identifiers, and timestamp interpretation. Invalid records are reported to the producer with examples. Production dashboards do not consume the feed until the initial contract check passes.',
 'A producer using an existing event type for a different business meaning must request a distinct contract review. Reusing a convenient type name can make old reports mix incompatible events. The registration record makes event meaning explicit rather than relying on a filename convention.'
], [
 'What information must a producer register before a new analytics feed is enabled?',
 'A sample delivery landed in storage. What must happen before dashboards can begin using that source?',
 'A producer wants to reuse an existing event name for a different business action. Is that merely a new file location?'
])
add('data', 'Analytics schema-change compatibility', [
 'A producer proposes a schema change with examples of the old and new event shapes and a list of known consumers. The data platform team checks compatibility before rollout. A field that looks unused in one dashboard may still be required by another registered consumer.',
 'Removing a required field or changing its meaning requires a new schema version and a migration plan for consumers. Adding an optional field can usually follow the compatible-change path after validation. The review distinguishes meaning changes from harmless extra information.',
 'During migration, producers keep the documented overlap period so consumers can move to the new version. The old event format is retired only after the consumer inventory is checked. Updating the producer code alone does not complete the downstream migration.'
], [
 'What should a producer provide when proposing an analytics event schema change?',
 'How does removing a required field differ from adding an optional field for compatibility review?',
 'The producer already emits the new event version. Can the previous format be retired before checking remaining consumers?'
])
add('data', 'Late-arriving event correction', [
 'The analytics pipeline assigns business events to reporting periods using their event timestamp rather than the time ingestion received them. Events arriving after the normal reporting cutoff are flagged as late. This distinction prevents delayed delivery from moving historical activity into the wrong business day.',
 'Late events within the seven-day correction window trigger a recalculation of the affected reporting partitions. Reports record the revised publication time. The team does not silently place the activity into today figures just to avoid revisiting a previously published partition.',
 'Events older than the automatic correction window enter a reviewed backfill request. The data owner approves the scope and identifies reports that will change. Replaying a large old delivery directly into production without that review can alter historical results unexpectedly.'
], [
 'Which timestamp assigns an analytics event to its business reporting period?',
 'An event arrives several days after its reporting cutoff but inside the correction window. How should its historical report be updated?',
 'A delivery contains events much older than the automatic correction window. Should the operator replay it directly into current production reports?'
])
add('data', 'Event replay deduplication', [
 'The ingestion system identifies a repeated event by its stable event identifier and producer namespace. It stores delivery attempts separately from accepted business events. Network retries must preserve the event identity so that a repeated delivery does not create another business action in analytics.',
 'An intentional correction to an accepted event uses the correction contract referencing the original event identifier. Assigning a new random identifier to unchanged content is not a correction mechanism. The audit trail must distinguish a revised fact from another attempted delivery of the same fact.',
 'Two different producers may use the same local identifier without describing the same event. Their producer namespaces keep those identities separate. Deduplicating solely on the local identifier could incorrectly discard a legitimate event from another source.'
], [
 'Which fields identify an event that has been delivered more than once?',
 'How should a producer correct an accepted business event rather than disguise a replay as a new event?',
 'Two producers both send an event numbered 42. Should one be discarded solely because its local identifier matches the other?'
])
add('data', 'Business-timezone reporting boundaries', [
 'Workspace reports group activity into business days using the timezone stored in the workspace reporting profile. Raw event timestamps remain stored as UTC instants. The display timezone of an analyst laptop is not used to determine the workspace day boundary.',
 'A reporting-timezone change takes effect from the next agreed reporting period and is recorded in report metadata. Existing published periods keep their original boundary interpretation unless the owner approves a historical recomputation. Merely changing a browser clock does not recalculate past reports.',
 'During a daylight-saving transition, a local business day may contain more or fewer than twenty-four elapsed hours. The pipeline uses calendar boundaries in the selected timezone rather than add a fixed number of seconds to find the next day. This prevents misplaced events near the transition.'
], [
 'Which timezone determines the day boundaries used in workspace reports?',
 'Does changing a workspace reporting timezone automatically reinterpret all already-published historical periods?',
 'How should business-day reporting handle a clock change that makes a local day shorter or longer than twenty-four hours?'
])
add('data', 'Shared metric definition approval', [
 'The analytics steward maintains each shared metric with its business question, formula, filters, owner, and unit. A metric name without those details is not a complete definition. Dashboards claiming to show the same metric should reference the same approved definition.',
 'A change to the population or calculation is reviewed as a definition revision, even if the display name stays unchanged. The steward identifies affected dashboards and records the effective date. Quietly changing a formula can make apparent trends reflect a definition shift rather than real business behavior.',
 'If two teams genuinely need different populations, the steward creates distinct clearly named metrics instead of forcing both into one ambiguous number. The relationship between the definitions is documented. Similar chart labels are not sufficient reason to treat different formulas as equivalent.'
], [
 'What information makes a shared analytics metric fully defined?',
 'Why does changing the filter population require review even when a chart keeps its old metric name?',
 'Two teams need different populations for their counts. Should they publish different formulas under one supposedly shared metric?'
])
add('data', 'Scoped analytics export delivery', [
 'An analytics export request specifies the dataset, permitted columns, time range, purpose, and named recipients. The data owner reviews the requested scope before preparing the file. Having dashboard access does not automatically authorize exporting every underlying column.',
 'Approved files are delivered through a recipient-restricted location with a forty-eight-hour download window. The export record captures the scope and delivery time. Sending the file as an unrestricted attachment in a general channel is not an approved substitute for that delivery path.',
 'If the requester needs a broader time range or extra columns after approval, the changed scope goes back to the data owner. Operators must not reuse an old approval as though it covered any future extraction. A revised file retains a link to the revised export request.'
], [
 'What scope information is required to request an analytics export?',
 'How are approved extraction files delivered to their named recipients?',
 'A requester adds columns after an export was approved. Can the operator treat the original approval as covering the expanded dataset?'
])
add('data', 'Scheduled analytics retention purge', [
 'The data retention worker removes eligible analytics records according to the dataset retention policy and cutoff timestamp. Before execution, it produces a preview of affected partitions and estimated rows. The dataset owner confirms that the cutoff matches the approved policy.',
 'A preservation marker on a partition removes that partition from the normal purge set. The worker records the skip and its reason rather than silently ignoring the marker. A storage-capacity alert does not authorize bypassing an active preservation instruction.',
 'After purge, the worker records actual removed partitions and refreshes dependent catalog state. An old dashboard cache can still display a previously computed aggregate, so the owner checks cache policy separately. Deleting source rows and clearing every derived view are not the same operation.'
], [
 'What preview should be reviewed before a scheduled analytics retention purge?',
 'Can a storage-pressure alert justify purging a partition that has an active preservation marker?',
 'Source records were purged but a dashboard still shows an older aggregate. Does that prove the underlying row deletion failed?'
])
add('data', 'Slow analytical query investigation', [
 'The data platform responder investigates a slow analytical query using its execution plan, scanned partitions, returned row count, and recent data-volume changes. A long elapsed time by itself does not show whether the cause is a broad scan, waiting on another job, or an inefficient operation.',
 'If the plan scans the entire history while the requested report covers one week, the owner checks whether the date predicate can prune partitions. Adding more compute is not the first repair for a missing scope condition. The corrected query must preserve the intended result definition.',
 'When a query is waiting behind another transaction or resource reservation, the responder identifies that blocker before changing indexes. A different index may not remove the wait. The incident record distinguishes time executing from time waiting for access to resources.'
], [
 'What evidence should be collected when an analytical query becomes slow?',
 'A one-week report scans years of data. What scope-related behavior should be checked before adding compute?',
 'The query is spending its time waiting for another transaction. Is rebuilding an index necessarily the right first action?'
])
add('data', 'Rebuilding a serving index', [
 'The data platform owner rebuilds a serving index from an approved source snapshot while the existing index remains available. The rebuild records the source checkpoint and target index version. Deleting the live index before constructing its replacement is not the standard rebuild method.',
 'The replacement passes count checks and representative query checks before an atomic serving-pointer switch. A completed build process alone is not sufficient for promotion. The owner confirms that the replacement contains the intended source checkpoint and can answer expected queries.',
 'If post-switch verification fails, the serving pointer can return to the retained prior index while the new build is inspected. The prior index is kept through the rollback window. Removing it immediately after promotion would eliminate that quick recovery option.'
], [
 'How should a serving index be rebuilt without taking the existing search path away?',
 'What validation is required before a freshly built index becomes the serving version?',
 'A newly promoted index fails verification. What retained object allows the serving pointer to be switched back quickly?'
])

# WORKPLACE OPERATIONS
add('workplace', 'Employee laptop purchase request', [
 'A manager requests a new employee laptop through the equipment catalog using the employee role, delivery location, and required start date. The device desk selects the approved role specification. A personal retail receipt is not a substitute for the normal company purchase request.',
 'Requests should arrive at least seven working days before the required start date. The desk records the expected delivery and any exception to the standard specification. A late request can be escalated, but an escalation does not guarantee that a new purchased device will arrive immediately.',
 'If an existing employee only needs a replacement while their assigned laptop is repaired, the desk checks the loaner pool instead of creating another permanent purchase. Temporary substitution and a new assigned asset are different equipment workflows.'
], [
 'What information should a manager include when requesting a new employee laptop?',
 'How early should a manager arrange a purchased device for an employee start date?',
 'An employee assigned laptop is being repaired for a few days. Should the desk immediately order another permanent laptop?'
])
add('workplace', 'Short-term loaner device checkout', [
 'The device desk issues a loaner laptop against the borrower employee identity, asset number, return date, and reason for temporary use. The borrower signs the checkout record. A loaner remains in the shared pool inventory rather than becoming a second permanently assigned employee asset.',
 'The standard borrowing period is ten working days. Extensions require the device desk to confirm pool availability before the return date. Keeping the device at home after the due date does not convert the temporary checkout into an approved extended assignment.',
 'On return, the desk records physical receipt and sends the device through its data-removal check before making it available to another borrower. Closing the borrowing ticket is not evidence that the laptop has been prepared for its next user.'
], [
 'What information is recorded when an employee borrows a loaner laptop?',
 'How can a temporary device borrower extend the normal ten-day borrowing period?',
 'A borrowed computer has been physically returned. Can it be handed straight to the next borrower before its data-removal check?'
])
add('workplace', 'Office visitor registration', [
 'An employee host registers an office visitor with the visit date, arrival time, company, and meeting purpose before arrival. Reception checks the visitor name against that registration. A forwarded meeting invitation alone does not create an approved building-access record.',
 'The host meets the visitor at reception and remains responsible for escorting them in staff-only areas. A visitor badge identifies the approved visit but is not an unrestricted employee pass. The visitor returns the badge when leaving the building.',
 'If the named host is absent, reception contacts an approved replacement host before admitting the visitor beyond the waiting area. The visitor is not sent to find a meeting room alone. The host responsibility must be transferred explicitly for that visit.'
], [
 'What should an employee register before inviting a visitor to the office?',
 'Does wearing a visitor badge allow a guest to move alone through staff-only office areas?',
 'A visitor arrives while their registered host is unavailable. What must reception arrange before admitting them further?'
])
add('workplace', 'Business travel booking approval', [
 'An employee requests business travel with the business purpose, destination, dates, and estimated transport and lodging costs. The manager approves the itinerary before the travel coordinator makes bookings. A calendar entry for an external meeting is not itself a travel approval.',
 'The coordinator uses the approved itinerary and records booking references in the travel case. If costs exceed the approved estimate by more than fifteen percent, the manager reviews the new amount before purchase. Staff do not split one itinerary into separate requests to conceal the total.',
 'A later change to travel dates is reviewed against cancellation terms and the remaining business purpose. The coordinator updates both the approval and the booking record where required. Editing the employee calendar does not automatically alter purchased tickets or hotel reservations.'
], [
 'What details are needed before business travel can be approved and booked?',
 'The proposed itinerary now costs substantially more than its approved estimate. What should happen before purchase?',
 'An employee moves the trip dates in their calendar. Does that also change the purchased tickets and hotel booking?'
])
add('workplace', 'Employee expense reimbursement', [
 'An employee submits an expense claim with itemized receipts, business purpose, payment date, and the linked approved activity. The finance desk checks the claim against that activity before reimbursement. A total copied from a card statement is not an itemized receipt.',
 'Claims should be submitted within ten working days after the activity ends. The manager confirms the business reason and the finance desk checks the evidence. Manager approval alone does not replace missing purchase details when an itemized record is required.',
 'An expense already paid directly by the company must not also be claimed as an employee outlay. The claimant identifies any prepaid items in the activity record. Reimbursing a personal payment and settling an existing company booking are distinct transactions.'
], [
 'Which supporting records are required for an employee expense reimbursement?',
 'How soon after an activity should an employee submit its reimbursement claim?',
 'The company already paid for a hotel directly. Should the employee include that amount as another personal reimbursement?'
])
add('workplace', 'Meeting-room equipment assistance', [
 'An employee reporting a meeting-room equipment problem identifies the room, meeting time, display connection, and whether audio or video is affected. The workplace desk checks the room equipment inventory. A report that a meeting does not work is too broad to identify the failing component.',
 'For a meeting already in progress, the desk first offers the documented fallback connection or another equipped room. It records the equipment fault for later repair. The immediate goal is to restore the meeting without requiring participants to wait for a complete hardware diagnosis.',
 'If the room equipment works with a known-good company device but not one attendee laptop, the case moves to employee-device support. The desk does not replace the room display solely because one laptop has a local adapter problem.'
], [
 'What information should be included when reporting a meeting-room audio or display problem?',
 'A meeting is already underway when its room display fails. What practical assistance should the desk offer first?',
 'The room display works with a test laptop but fails with one attendee device. Should the display automatically be replaced?'
])
add('workplace', 'Receiving office deliveries', [
 'Reception records an incoming office parcel with the carrier reference, arrival time, and intended employee or team. The recipient receives a collection notice after the parcel is logged. A delivery driver signature does not prove that the named employee has personally collected the item.',
 'Uncollected parcels remain in the reception holding area for five working days before the workplace coordinator contacts the recipient manager. Perishable or unusually large deliveries are escalated sooner. Reception must not mark a package collected simply to clear its waiting list.',
 'A parcel addressed to a former employee is routed to the workplace coordinator for ownership review. It is not opened by any staff member who recognizes the name. The coordinator checks whether the item belongs to a company purchase or requires return to the sender.'
], [
 'What should reception record when an office parcel arrives?',
 'How long does a normal uncollected parcel remain before the recipient manager is contacted?',
 'A parcel arrives for someone who has left the company. Can any colleague open it because they recognize the former employee name?'
])
add('workplace', 'Ergonomic equipment assessment', [
 'An employee requesting ergonomic equipment describes their work setup and the adjustment they need through the workplace assessment form. The workplace coordinator reviews the setup with the employee before selecting equipment. The process is a workplace fit assessment, not a diagnosis or medical consultation.',
 'The coordinator can arrange a short trial of an approved chair, monitor arm, or input device before a permanent assignment. The trial record includes the item and review date. Trying one item does not authorize purchasing any unlisted equipment independently.',
 'If an item does not address the reported setup problem, the coordinator reviews the trial outcome and considers another approved adjustment. The employee should not retain several trial items indefinitely without a decision. The goal is a documented effective setup rather than an accumulating equipment collection.'
], [
 'How should an employee request an assessment for ergonomic work equipment?',
 'Can an employee trial approved equipment before it is permanently assigned?',
 'The first trial item did not improve the work setup. What should happen instead of retaining multiple trial items indefinitely?'
])
add('workplace', 'Employee learning-budget request', [
 'An employee proposes a learning purchase with the skill objective, provider, cost, and connection to current or planned work. The manager checks available learning budget before approval. A course being popular with other employees does not establish that it fits the requesting person work needs.',
 'Approval must be recorded before the course or conference is purchased. The learning coordinator records the provider and enrollment reference after purchase. An employee cannot assume that an unapproved personal purchase will automatically be reimbursed from the learning budget.',
 'If the employee cannot attend, they notify the coordinator before the provider cancellation deadline so a transfer or refund can be considered. Simply not using the course does not restore the company budget. The coordinator records the actual outcome of the cancellation request.'
], [
 'What business justification and cost details are needed for a learning-budget request?',
 'Can an employee purchase a course personally and assume it will automatically be reimbursed without prior approval?',
 'An approved learner can no longer attend. What action could preserve value before the provider cancellation deadline?'
])
add('workplace', 'Home-connectivity allowance submission', [
 'A remote employee can submit a home-connectivity allowance claim with a provider bill, covered service period, and confirmation of their active remote-work arrangement. The workplace coordinator checks eligibility before finance processes the allowance. This is separate from troubleshooting a failed connection.',
 'The allowance covers one eligible connection period per employee and cannot be claimed twice through different departments. The claim record identifies the service period so finance can detect overlap. Moving teams does not create a second allowance for the same month.',
 'An equipment purchase such as a router is not automatically covered by the recurring connectivity allowance. The employee requests equipment approval through the device or workplace catalog instead. A provider bill and a hardware invoice follow different approval paths.'
], [
 'What evidence supports a remote employee home-connectivity allowance claim?',
 'An employee changed departments during a month. Can both departments pay a connectivity allowance for that same service period?',
 'Does the recurring home-internet allowance automatically authorize reimbursement for a newly purchased router?'
])

# SOFTWARE DELIVERY AND ENGINEERING QUALITY
add('engineering', 'Routing a code-change review', [
 'A change author requests review from a maintainer for each affected component and describes the intended behavior and validation performed. The component ownership map identifies the required reviewers. Choosing a convenient available teammate is not sufficient when that person cannot approve the changed component.',
 'A change that crosses component boundaries requires the relevant maintainers to coordinate their approvals. One maintainer approval does not automatically cover every other component in the same branch. The author records any explicit delegated review so the responsibility remains visible.',
 'If the normal maintainer is unavailable, the engineering duty lead names an authorized substitute. The author does not approve their own change merely because the primary reviewer is away. Urgent incident work can use the emergency release path while retaining its required independent review.'
], [
 'How should a code-change author determine which maintainers must review a change?',
 'A branch changes several independently owned components. Does approval from one component maintainer cover all of them?',
 'The normal code reviewer is away. What authorized route should be used instead of self-approving the change?'
])
add('engineering', 'Flaky-test quarantine and repair', [
 'A test can be quarantined when repeated runs demonstrate inconsistent results under unchanged code and comparable conditions. The owning team records evidence, a repair owner, and an expiry date for the quarantine. One failure after a real code change is not sufficient evidence of flakiness.',
 'Quarantined tests continue to run in a separate visible job while their failures stop blocking the standard release gate. The team tracks those results so repair progress remains observable. Quarantine does not mean deleting the test or hiding its execution history.',
 'If investigation shows a genuine product defect rather than unstable test behavior, the case returns to the normal defect and release decision process. The quarantine label must not be used to ship a reproducible regression merely because the failing test is inconvenient.'
], [
 'What evidence is required before a test can be classified as flaky and quarantined?',
 'Do quarantined tests stop running, or are their results still collected somewhere visible?',
 'A supposedly flaky test reveals a repeatable product regression. Should its quarantine label allow the regression to pass unnoticed?'
])
add('engineering', 'Urgent security patch release', [
 'The security duty lead can request an urgent patch for a confirmed exposure that cannot wait for the standard release schedule. The service owner identifies the affected versions, proposed correction, and deployment risk. Urgency changes the schedule rather than remove the need to understand the patch.',
 'The patch receives focused independent review and targeted regression checks before deployment. The incident or security case records which normal checks were deferred and who accepted that decision. A fast release still has a traceable approval and a rollback or recovery plan.',
 'If a release freeze is active, the security patch also receives the freeze-exception authorization appropriate to its impact. The security finding alone does not silently clear every release-control gate. The linked records show both the exposure decision and the permission to deploy during the freeze.'
], [
 'Who can initiate an urgent security patch outside the standard release schedule?',
 'What review and validation should remain visible when some normal checks are deferred for an emergency patch?',
 'A security correction must ship during a release freeze. Does the finding itself replace the separate freeze-exception authorization?'
])
add('engineering', 'Routine dependency version upgrade', [
 'A component owner proposes a routine dependency upgrade with the current version, target version, reason, and upstream compatibility notes. The change identifies direct and relevant transitive effects. A newer release being available is not by itself evidence that the application behavior will remain compatible.',
 'The owner runs representative component tests and checks build and packaging behavior after updating the lock file. The reviewed source change includes the resolved dependency state. Updating only the version declaration while leaving the actual resolution unexplained is not a complete upgrade record.',
 'A dependency update addressing a confirmed urgent exposure can move through the security patch process instead of the ordinary schedule. The owner still records the exact version and compatibility evidence. Reclassifying the timing does not justify an unbounded update of unrelated dependencies.'
], [
 'What compatibility information should accompany a routine dependency upgrade?',
 'What should reviewers see besides a changed version declaration when a dependency is upgraded?',
 'One dependency needs an urgent security fix. Does that justify upgrading unrelated dependencies without checking their compatibility?'
])
add('engineering', 'Retiring a completed feature flag', [
 'The feature owner retires a rollout flag only after the selected behavior is stable and every registered consumer has moved to the intended state. The change removes obsolete branches and configuration references. A flag being enabled for most users is not proof that no client still depends on its old behavior.',
 'The owner checks background jobs, tests, dashboards, and emergency procedures for flag references before deleting the configuration entry. Removing the flag service record first can leave consumers reading a missing value. Code and configuration cleanup are coordinated as one retirement change.',
 'If the flag remains part of an active rollback plan, the release owner decides when that recovery need has ended. The team does not remove the rollback control solely to improve a cleanup count. Operational use and long-term feature selection are considered separately.'
], [
 'What must a feature owner establish before retiring a rollout flag?',
 'Why should code, background jobs, and operational references be checked before deleting a feature-flag configuration entry?',
 'A feature is fully enabled, but its flag is still required by the active rollback plan. Should the flag be deleted just to finish cleanup?'
])
add('engineering', 'Large binary artifact versioning', [
 'Engineering repositories keep source and small reviewable fixtures in ordinary version history, while large generated binaries are stored in the artifact registry. The source record links a content digest and build reference to the binary. Uploading a large output directly to every source commit is not the standard distribution path.',
 'A reproducible artifact reference identifies both the producing source revision and the immutable artifact digest. A mutable latest label alone is insufficient for a rollback record. Reviewers must be able to identify the exact bytes deployed from a particular build.',
 'If a large binary was committed accidentally, the owner first moves distribution to the registry and assesses whether published history requires a coordinated rewrite. Simply deleting the file in a new commit does not remove its bytes from older commits. Collaborators must be warned before any shared history rewrite.'
], [
 'Where should a team store large generated binary outputs rather than attach them to every source commit?',
 'Why is a mutable latest artifact label insufficient to reproduce an old deployment?',
 'A huge binary was removed in a later commit. Does that alone remove its contents from the repository historical revisions?'
])
add('engineering', 'Release-freeze exception approval', [
 'During a declared release freeze, the change owner requests an exception with customer impact, risk, required timing, and a recovery plan. The duty release manager approves or rejects the exception. A passing automated build does not independently authorize deployment during the freeze.',
 'An approval identifies the exact change and permitted deployment window. It cannot be reused for unrelated work on the same branch. If the proposed release scope expands, the owner returns to the release manager rather than treating the original exception as a general permission slip.',
 'An incident rollback that restores a previously approved state follows the incident commander recovery authority and is recorded in the freeze log. A new feature bundled with that rollback still needs its own exception decision. Recovery authority must not be used to hide unrelated feature delivery.'
], [
 'What information is needed to request permission to deploy during a release freeze?',
 'Can a freeze exception for one specific correction be reused for unrelated work on the same branch?',
 'An incident requires rolling back during a freeze. Can a new feature be bundled into that recovery action without a separate decision?'
])
add('engineering', 'Comparable load-test baselines', [
 'A performance comparison records workload shape, concurrency, dataset size, runtime configuration, and the exact program build. The test owner holds these conditions stable when comparing two changes. Faster elapsed time under a lighter workload is not evidence that the changed program is more efficient.',
 'The owner reports latency percentiles, achieved throughput, and resource observations after a documented warm-up. A single average latency can hide a small fraction of very slow requests. Failures and timeouts remain in the result accounting rather than disappearing from the summary.',
 'If another heavy job used the same machine during one run, the owner labels the contention and repeats the affected comparison under comparable conditions. The shared-host result can be retained as an observation, but it is not presented as a controlled capacity guarantee.'
], [
 'Which workload and runtime details must be held comparable for a load-test baseline?',
 'Why should a performance report include latency percentiles and failed requests rather than only an average?',
 'One benchmark run shared its host with another heavy job. Can its speed difference be reported as a controlled capacity improvement without qualification?'
])
add('engineering', 'Configuration drift reconciliation', [
 'The service owner compares observed runtime settings with the approved configuration record when drift is detected. The review identifies who changed the setting, why it changed, and whether the change was authorized. A difference alone does not establish which side should automatically overwrite the other.',
 'An authorized emergency adjustment is reconciled by either updating the approved configuration through review or returning the runtime to the intended value. The decision includes the operational reason. Leaving a manual exception undocumented invites it to be lost on the next ordinary deployment.',
 'A drift alert involving a secret value records only its identifier and fingerprint in the general change record. The actual secret stays in its approved storage system. Publishing sensitive values in a diff is not required to prove that a configuration changed.'
], [
 'What should a service owner establish when observed settings differ from the approved configuration?',
 'How should a legitimate emergency runtime adjustment be reconciled with the versioned configuration?',
 'A configuration drift involves a secret. Must the actual secret value be pasted into the ordinary change diff?'
])
add('engineering', 'Breaking API contract release', [
 'An API owner treats removal of a supported field, change of its meaning, or a newly mandatory request field as a potentially breaking contract change. The proposal identifies affected clients and the replacement behavior. Passing server-side tests alone does not prove that existing clients can continue working.',
 'The owner publishes a migration guide and an overlap window for a new major contract version. Registered client owners confirm their migration status before the previous contract is withdrawn. The version number is a communication tool, not a substitute for coordinating the client transition.',
 'An internal implementation refactor that preserves accepted requests and response meaning can use the compatible release path. The team does not require every internal rewrite to become a new public major version. The distinction follows observable client behavior rather than the size of the source diff.'
], [
 'Which kinds of API behavior change should be assessed as potentially breaking for clients?',
 'What should happen before withdrawing an old API contract after a new major version is published?',
 'A large internal rewrite preserves the existing requests and response meaning. Does source-change size alone require a new major API contract?'
])

# Additional multi-article tasks. Both targets are necessary sources for the
# explicitly combined question; each is independently useful to answer it.
MULTI = [
 ('How do we revoke a departing employee personal access and transfer ownership of automated service identities they supported?', [8,5]),
 ('What procedures cover recovering a lost sign-in phone and containing a missing company laptop at the same time?', [3,10]),
 ('How do we authorize temporary administrator rights and certify whether existing standing resource permissions are still needed each quarter?', [7,9]),
 ('Which procedures distinguish routine API-key replacement from an exposed credential that requires immediate containment?', [6,36]),
 ('How do we recover a mistakenly deleted database record and separately restore a deleted shared document?', [11,12]),
 ('What should we check when a backup job lacks its completion acknowledgment and another retained set fails an integrity checksum?', [20,14]),
 ('Which instructions cover keeping selected backup sets on a case hold and deciding when an old backup decryption key can be retired?', [16,17]),
 ('How do we plan a DNS destination cutover and verify the public certificate served by its new edge nodes?', [21,22]),
 ('What procedures cover draining accepted node connections and deciding whether a canary release is ready for more traffic?', [29,30]),
 ('How do we troubleshoot an employee VPN tunnel and separately arrange reimbursement for that employee eligible home connection?', [24,90]),
 ('Which records explain assigning incident priority and publishing customer-facing incident progress updates?', [31,33]),
 ('What should the team record during incident response and how should it turn that record into a later learning review?', [32,35]),
 ('How should we distinguish a refund request for a subscription from reconciliation of two captured payments for one order?', [51,53]),
 ('Which procedures cover correcting an already-issued invoice and changing the currency used for future subscription charges?', [55,58]),
 ('How should we handle a payment dispute while considering whether a customer should receive account credit rather than returned cash?', [59,60]),
 ('What procedures distinguish damaged goods arriving from a supplier from goods sent back by a customer?', [63,66]),
 ('How do we conduct a blind cycle count and investigate a quantity correction when its recount still disagrees with the stock system?', [68,62]),
 ('Which procedures cover making sense of late-arriving business events and assigning those events to the correct local reporting day?', [73,75]),
 ('How do we plan an analytics schema migration and coordinate a separately versioned breaking client-facing API contract?', [72,100]),
 ('What procedures authorize an urgent security correction and its deployment while a release freeze is active?', [93,97]),
]
