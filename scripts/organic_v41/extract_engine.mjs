// Read-only inspection preparation. Never execute or modify game bundles.
// Run from workspace; extraction stays under work/, not the published mod.
import * as asar from '../../../../work/map-tools/node_modules/@electron/asar/lib/asar.js';
import fs from 'node:fs';
const archive='/Applications/Subway Builder.app/Contents/Resources/app.asar';
const scratch='work/organic-v41';
fs.mkdirSync(scratch,{recursive:true});
for (const name of asar.listPackage(archive).filter(x=>/renderer.*\.js$/.test(x))) {
  const data=asar.extractFile(archive,name.slice(1));
  if (data.includes('residenceId')) fs.writeFileSync(`${scratch}/engine-${name.split('/').pop()}`,data);
}
