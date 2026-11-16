
figma.showUI(__html__, {
  width: 320,
  height: 240
});

figma.ui.onmessage = async (msg) => {
  if (msg.type !== "add-swatch") return;

  try {
    const color = msg.color;

    if (!color || !/^#[0-9A-F]{6}$/i.test(color.hex || "")) {
      throw new Error("Invalid color data");
    }

    const r = color.r;
    const g = color.g;
    const b = color.b;

    await figma.loadFontAsync({
      family: "Inter",
      style: "Regular"
    });

    const frame = figma.createFrame();

    frame.name = `OpenCV - ${color.name} ${color.hex}`;
    frame.resize(220, 150);
    frame.fills = [];

    const swatch = figma.createRectangle();

    swatch.name = color.hex;
    swatch.resize(196, 85);
    swatch.x = 12;
    swatch.y = 12;

    swatch.fills = [{
      type: "SOLID",
      color: {
        r: r / 255,
        g: g / 255,
        b: b / 255
      }
    }];

    frame.appendChild(swatch);

    const label = figma.createText();

    label.fontName = {
      family: "Inter",
      style: "Regular"
    };

    label.characters = `${color.name} | ${color.hex}`;
    label.fontSize = 12;
    label.x = 12;
    label.y = 110;

    frame.appendChild(label);

    const existing = figma.currentPage.children.filter(
      node => node.name.startsWith("OpenCV -")
    );

    if (existing.length > 0) {
      frame.x = Math.max(
        ...existing.map(node => node.x + node.width)
      ) + 20;

      frame.y = existing[0].y;
    } else {
      frame.x = figma.viewport.center.x - 110;
      frame.y = figma.viewport.center.y - 75;
    }

    figma.currentPage.appendChild(frame);

    figma.currentPage.selection = [frame];

    figma.viewport.scrollAndZoomIntoView([frame]);

    figma.notify(`Color added: ${color.hex}`);

    figma.ui.postMessage({
      type: "success",
      message: `Added ${color.name} ${color.hex}`
    });

  } catch (error) {
    console.error("OpenCV Error:", error);

    figma.notify(
      error.message || "Failed to add color"
    );

    figma.ui.postMessage({
      type: "error",
      message: error.message || "Failed to add color"
    });
  }
};
