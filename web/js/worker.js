/* Pyodide worker: load runtime, unpack py_bundle.zip, dispatch web_api calls. */

const PYODIDE_VERSION = "0.26.4";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

let pyodide = null;
let ready = false;

function post(msg) {
  self.postMessage(msg);
}

function setProgress(message) {
  post({ type: "progress", message });
}

async function init() {
  try {
    setProgress("Downloading Pyodide…");
    importScripts(`${PYODIDE_CDN}pyodide.js`);
    pyodide = await loadPyodide({ indexURL: PYODIDE_CDN });

    setProgress("Fetching Python bundle…");
    const bundleResp = await fetch("../py_bundle.zip");
    if (!bundleResp.ok) {
      throw new Error(`Failed to fetch py_bundle.zip (${bundleResp.status}). Run: python tools/build_web.py`);
    }
    const bundleBuf = await bundleResp.arrayBuffer();
    pyodide.unpackArchive(bundleBuf, "zip");

    setProgress("Importing game code…");
    await pyodide.runPythonAsync("import web_api");

    setProgress("Loading maps…");
    const mapsResp = await fetch("../data/maps.json");
    if (!mapsResp.ok) {
      throw new Error(`Failed to fetch maps.json (${mapsResp.status})`);
    }
    const mapsText = await mapsResp.text();
    pyodide.globals.set("_maps_json", mapsText);
    await pyodide.runPythonAsync("web_api.load_maps_json(_maps_json)");

    setProgress("Loading Q-tables…");
    try {
      const indexResp = await fetch("../data/models/index.json");
      if (indexResp.ok) {
        const index = await indexResp.json();
        const items = [];
        for (const item of index.items || []) {
          const file = (item.file || "").replace(/^\.\//, "../");
          const modelResp = await fetch(file);
          if (!modelResp.ok) continue;
          const data = await modelResp.json();
          items.push({ role: item.role, data });
        }
        pyodide.globals.set("_models_json", JSON.stringify({ items }));
        await pyodide.runPythonAsync("web_api.load_models_json(_models_json)");
      }
    } catch (_) {
      /* models optional */
    }

    ready = true;
    post({ type: "ready" });
  } catch (err) {
    post({ type: "init_error", error: String(err && err.message ? err.message : err) });
  }
}

self.onmessage = async (event) => {
  const data = event.data || {};
  if (data.type === "init") {
    await init();
    return;
  }
  if (!ready || !pyodide) {
    post({ id: data.id, error: "Pyodide is not ready yet" });
    return;
  }
  const { id, fn, args } = data;
  try {
    pyodide.globals.set("_fn", fn);
    pyodide.globals.set("_args_json", JSON.stringify(args || []));
    const resultJson = await pyodide.runPythonAsync(`
import json
import web_api
_args = json.loads(_args_json)
_result = web_api.call(_fn, _args)
json.dumps(_result)
`);
    const result = JSON.parse(resultJson);
    if (result && result.error) {
      post({ id, error: result.error });
    } else {
      post({ id, result });
    }
  } catch (err) {
    post({ id, error: String(err && err.message ? err.message : err) });
  }
};
