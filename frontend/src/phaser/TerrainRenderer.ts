import Phaser from "phaser";
import { NES } from "./nesColors";
import {
  BUILDINGS,
  createBuilding,
  createCastle,
  drawPaths,
  drawRiverAndPond,
  drawForestClusters,
  drawMountainClusters,
} from "./sceneAssets";

export interface TerrainConfig {
  scene: Phaser.Scene;
  worldInner: Phaser.GameObjects.Container;
  worldContainer: Phaser.GameObjects.Container;
  width: number;
  height: number;
}

export class TerrainRenderer {
  private scene: Phaser.Scene;
  private worldInner: Phaser.GameObjects.Container;
  private buildingRects: Map<string, Phaser.GameObjects.Container> = new Map();

  constructor(config: TerrainConfig) {
    this.scene = config.scene;
    this.worldInner = config.worldInner;
    this.render(config.width, config.height);
  }

  getBuilding(key: string): Phaser.GameObjects.Container | undefined {
    return this.buildingRects.get(key);
  }

  getAllBuildings(): Map<string, Phaser.GameObjects.Container> {
    return this.buildingRects;
  }

  private render(w: number, h: number) {
    const cx = w / 2;
    const cy = h / 2;

    // 1. 地形层 — NES 草地
    const grass = this.scene.add.tileSprite(0, 0, w + 64, h + 64, "grass");
    grass.setTileScale(1);
    this.worldInner.add(grass);

    // 2. 道路层
    drawPaths(this.scene, this.worldInner, cx, cy);

    // 3. 河流
    drawRiverAndPond(this.scene, this.worldInner, cx, cy);

    // 4. 装饰层 — 散落小石头
    const stonePositions = [
      { x: 255, y: 200 }, { x: 385, y: 280 },
      { x: 200, y: 240 }, { x: 440, y: 224 },
      { x: 280, y: 360 }, { x: 360, y: 120 },
      { x: 170, y: 300 }, { x: 460, y: 290 },
    ];
    stonePositions.forEach(({ x, y }) => {
      const stone = this.scene.add.image(x - cx, y - cy, "stone");
      this.worldInner.add(stone);
    });

    // 5. 森林/山脉层 — 前后层叠
    drawForestClusters(this.scene, this.worldInner, cx, cy);
    drawMountainClusters(this.scene, this.worldInner, cx, cy);

    // 6. 建筑层（跳过任务中心，由分散 NPC 替代）
    Object.entries(BUILDINGS).forEach(([key, b]) => {
      if (key === "task") return;
      const container = key === "square"
        ? createCastle(this.scene, b.x - cx, b.y - cy, b.label)
        : createBuilding(this.scene, key, b.x - cx, b.y - cy, b.w, b.h, b.roof, b.label, b.color);
      this.worldInner.add(container);
      this.buildingRects.set(key, container);
    });
  }
}

export interface UIConfig {
  scene: Phaser.Scene;
  width: number;
  height: number;
}

export class UIRenderer {
  private scene: Phaser.Scene;
  private subtitleContainer!: Phaser.GameObjects.Container;
  private subtitleText!: Phaser.GameObjects.Text;
  private subtitleQueue: Array<{ text: string; level: string }> = [];
  private subtitlePlaying = false;

  constructor(config: UIConfig) {
    this.scene = config.scene;
    this.render(config.width, config.height);
  }

  private render(w: number, h: number) {
    // 标题栏
    const titleBg = this.scene.add.graphics();
    titleBg.fillStyle(NES.BLACK, 1);
    titleBg.fillRect(0, 0, w, 24);
    titleBg.lineStyle(1, NES.WHITE, 1);
    titleBg.strokeRect(0, 0, w, 24);
    titleBg.setDepth(900);
    titleBg.setScrollFactor(0);

    const titleText = this.scene.add.text(w / 2, 12, "EVOTOWN", {
      fontSize: "14px",
      color: "#F8F8F8",
      fontStyle: "bold",
    }).setOrigin(0.5).setResolution(2);
    titleText.setDepth(901);
    titleText.setScrollFactor(0);

    // 字幕 HUD
    const subBg = this.scene.add.graphics();
    subBg.fillStyle(0x000000, 0.82);
    subBg.fillRect(0, h - 36, w, 36);
    subBg.lineStyle(2, 0xf97316, 1);
    subBg.strokeRect(0, h - 36, w, 36);
    subBg.setDepth(950).setScrollFactor(0);

    this.subtitleText = this.scene.add.text(w + 20, h - 18, "", {
      fontSize: "13px",
      color: "#fbbf24",
      fontStyle: "bold",
    }).setOrigin(0, 0.5).setDepth(951).setScrollFactor(0).setResolution(2);

    this.subtitleContainer = this.scene.add.container(0, 0, [subBg, this.subtitleText]);
    this.subtitleContainer.setDepth(950).setScrollFactor(0).setVisible(false);
  }

  pushSubtitle(text: string, level: string) {
    this.subtitleQueue.push({ text, level });
    if (!this.subtitlePlaying) this.playNextSubtitle();
  }

  private playNextSubtitle() {
    if (this.subtitleQueue.length === 0) {
      this.subtitlePlaying = false;
      this.subtitleContainer.setVisible(false);
      return;
    }
    this.subtitlePlaying = true;
    const { text, level } = this.subtitleQueue.shift()!;

    const colors: Record<string, string> = {
      last_stand: "#ff6666",
      elimination: "#ff4444",
      defection: "#ff9933",
      info: "#fbbf24",
    };
    const color = colors[level] ?? "#fbbf24";
    const w = this.scene.scale.width;
    const h = this.scene.scale.height;

    this.subtitleContainer.setVisible(true);
    this.subtitleText
      .setText(text)
      .setColor(color)
      .setAlpha(1)
      .setX(w + 20);

    this.scene.tweens.add({
      targets: this.subtitleText,
      x: 12,
      duration: 500,
      ease: "Cubic.easeOut",
      onComplete: () => {
        this.scene.time.delayedCall(3500, () => {
          this.scene.tweens.add({
            targets: this.subtitleText,
            alpha: 0,
            x: -w,
            duration: 600,
            ease: "Cubic.easeIn",
            onComplete: () => {
              this.subtitleText.setX(w + 20).setAlpha(1);
              this.playNextSubtitle();
            },
          });
        });
      },
    });

    if (level === "elimination") {
      this.scene.cameras.main.flash(200, 80, 0, 0, false);
    } else if (level === "last_stand") {
      this.scene.cameras.main.flash(150, 60, 0, 0, false);
    }
    void h;
  }

  getWidth(): number {
    return this.scene.scale.width;
  }

  getHeight(): number {
    return this.scene.scale.height;
  }
}
