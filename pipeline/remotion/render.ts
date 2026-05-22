import * as fs from "fs";
import * as path from "path";
import { renderMedia, selectComposition, ensureBrowser } from "@remotion/renderer";

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: ts-node render.ts <scene_json_path> <output_mp4_path>");
    process.exit(1);
  }

  const [sceneJsonPath, outputPath] = args;
  const layout = JSON.parse(fs.readFileSync(sceneJsonPath, "utf8"));

  const serveUrl = path.join(__dirname, "src");

  await ensureBrowser();

  const composition = await selectComposition({
    serveUrl,
    id: "Scene",
    inputProps: { layout },
  });

  await renderMedia({
    composition,
    serveUrl,
    codec: "h264",
    outputLocation: outputPath,
    inputProps: { layout },
    concurrency: 1,
    timeoutInMilliseconds: 180_000,
    onProgress: ({ progress }) => {
      const pct = Math.round(progress * 100);
      process.stdout.write(`\rprogress:${pct}`);
    },
  });

  process.stdout.write("\n");
  console.log(`done:${outputPath}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
