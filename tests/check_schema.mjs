import {PGlite} from '@electric-sql/pglite';
import fs from 'node:fs';
const db=new PGlite();await db.exec('CREATE ROLE anon; CREATE ROLE authenticated;');
const root=new URL('../supabase/',import.meta.url).pathname;const files=fs.readdirSync(root).filter(n=>/^\d{3}_.*\.sql$/.test(n)).sort();
for(const file of files){await db.exec(fs.readFileSync(root+'/'+file,'utf8'));console.log('Applied',file)}
for(const file of files)await db.exec(fs.readFileSync(root+'/'+file,'utf8'));
const tables=(await db.query("SELECT table_name FROM information_schema.tables WHERE table_schema='promptto'")).rows;
console.log('PostgreSQL engine schema checks passed:',tables.length,'tables; migrations safely repeated');
await db.exec("INSERT INTO promptto.users VALUES('u','Schema User','schema@example.com','hash',0); INSERT INTO promptto.accounts VALUES('a','Schema account','schema-account','2026-10-12');INSERT INTO promptto.projects VALUES('p','a','Schema project','','active',NULL,'2026-10-12');INSERT INTO promptto.traction_sources VALUES('s','a','p','collected','spreadsheet',NULL,'2026-10-12'); INSERT INTO promptto.traction_values VALUES('a','p','collected','2026-10-12',123456789.25,'s','2026-10-12');");
const value=(await db.query("SELECT value FROM promptto.traction_values WHERE source_id='s'")).rows[0].value;console.log('Stored traction amount:',value);if(Number(value)!==123456789.25)throw Error('Traction money loses precision in PostgreSQL REAL');
await db.exec(fs.readFileSync(root+'/runtime_permissions.sql','utf8'));
const grants=(await db.query("SELECT has_schema_privilege('anon','promptto','USAGE') exposed,has_table_privilege('gazal_app','promptto.policy_versions','UPDATE') editable")).rows[0];if(grants.exposed||grants.editable)throw Error('Schema/audit permissions are too broad');
await db.exec("INSERT INTO promptto.tasks VALUES('t','a','p','u','Review task','','medium',3,'submitted','2026-10-12','2026-10-12','2026-10-12','2026-10-12',NULL);INSERT INTO promptto.reviews VALUES('r','a','t','u','approved',88.1234,'Checked','2026-10-12');");
const quality=(await db.query("SELECT quality FROM promptto.reviews WHERE id='r'")).rows[0].quality;if(quality!==88.1234)throw Error('Fractional quality lost');
console.log('Schema access, immutable-policy permissions and fractional quality checks passed');
await db.close();
const fresh=new PGlite();await fresh.exec('CREATE ROLE anon;CREATE ROLE authenticated;');await fresh.exec(fs.readFileSync(root+'/schema.sql','utf8'));console.log('Fresh SQL export passed');await fresh.close();
