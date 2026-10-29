import { app } from "../../scripts/app.js";
import { addTextLabel } from "./tony4896_io.js";

const ROW_H = 20;
const MARGIN = 15;
const X_W = 18;

function itemWidgets(node) { return node.widgets.filter(w => w.name.startsWith("item_")); }
function findWidget(node, name) { return node.widgets.find(w => w.name === name); }

function syncItems(node) {
    const n = itemWidgets(node).length;
    findWidget(node, "Total Items").value = String(n);
    const index = findWidget(node, "index");
    // control_after_generate "randomize" draws from [min, max), so max = n gives 0..n-1.
    index.options.max = n;
    if (index.value > n) index.value = n;
    const h = node.computeSize()[1];
    if (node.size[1] < h) node.setSize([node.size[0], h]);
    node.setDirtyCanvas(true, true);
}

function addItem(node, value = "") {
    node.__tonyItemCounter = (node.__tonyItemCounter || 0) + 1;
    const row = {
        name: `item_${node.__tonyItemCounter}`, type: "custom", value, options: {},
        computeSize(width) { return [width, ROW_H]; },
        draw(ctx, node, width, y) {
            const textY = y + ROW_H * 0.7;
            ctx.save();
            ctx.fillStyle = "#222";
            ctx.strokeStyle = "#666";
            ctx.beginPath();
            ctx.roundRect(MARGIN, y, width - MARGIN * 2, ROW_H, ROW_H * 0.5);
            ctx.fill();
            ctx.stroke();
            ctx.beginPath();
            ctx.rect(MARGIN, y, width - MARGIN * 2, ROW_H);
            ctx.clip();
            ctx.fillStyle = "#999";
            ctx.textAlign = "left";
            ctx.fillText(this.name, MARGIN * 2, textY);
            ctx.textAlign = "right";
            ctx.fillText("\u2715", width - MARGIN - 7, textY);
            let text = String(this.value ?? "").replace(/\s+/g, " ");
            const maxW = width - MARGIN * 4 - ctx.measureText(this.name).width - X_W;
            if (ctx.measureText(text).width > maxW) {
                while (text.length && ctx.measureText(text + "\u2026").width > maxW) text = text.slice(0, -1);
                text += "\u2026";
            }
            ctx.fillStyle = text ? "#ddd" : "#777";
            ctx.fillText(text || "click to edit", width - MARGIN - X_W, textY);
            ctx.restore();
        },
        mouse(event, pos, node) {
            if (event.type !== "pointerup") return false;
            if (pos[0] > node.size[0] - MARGIN - X_W) {
                node.removeWidget(this);
            } else {
                app.canvas.prompt("Item", this.value, (v) => {
                    this.value = String(v ?? "");
                    node.setDirtyCanvas(true, true);
                }, event, true);
            }
            syncItems(node);
            return true;
        },
    };
    node.widgets.splice(node.widgets.indexOf(findWidget(node, "Add item")), 0, row);
    return row;
}

app.registerExtension({
    name: "Tony4896.SelectRandom",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "Select_Random") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            const button = this.addWidget("button", "Add item", null, () => { addItem(this); syncItems(this); });
            button.serialize = false;
            button.options.serialize = false;
            const total = addTextLabel(this, "Total Items", "0");
            total.serialize = false;
            for (const name of ["index", "control_after_generate"]) {
                const w = findWidget(this, name);
                this.widgets.splice(this.widgets.indexOf(w), 1);
                this.widgets.push(w);
            }
            syncItems(this);
        };

        // Saved workflows map widgets_values by position, so the rows must exist
        // before LiteGraph assigns values. Rows = values minus the fixed serialized widgets.
        const configure = nodeType.prototype.configure;
        nodeType.prototype.configure = function (info) {
            for (const w of itemWidgets(this)) this.removeWidget(w);
            const fixed = this.widgets.filter(w => w.serialize !== false).length;
            const n = Math.max(0, (info.widgets_values?.length ?? 0) - fixed);
            for (let i = 0; i < n; i++) addItem(this);
            configure.apply(this, arguments);
            syncItems(this);
        };
    },
});
