// File: web/save_image_a1111_metadata_extra_output.js
import { app } from "../../scripts/app.js";
import { applyTextReplacements } from "../../scripts/utils.js";

const SAVE_NODE_TYPES = new Set([
  "SaveImageA1Metadata",
]);

function findWidget(node, name) {
  return node?.widgets?.find((w) => w?.name === name) ?? null;
}

app.registerExtension({
  name: "Tony4896.SaveImageA1111MetadataExtraOutput",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    console.log("Tony extension loaded");
    console.log("beforeRegisterNodeDef:", nodeData.name);
    if (SAVE_NODE_TYPES.has(nodeData.name)) {
      const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

      nodeType.prototype.onNodeCreated = function () {
        const result = originalOnNodeCreated
          ? originalOnNodeCreated.apply(this, arguments)
          : undefined;

        const widget = findWidget(this, "filename_prefix");
        if (!widget) {
          return result;
        }

        const originalSerializeValue = widget.serializeValue?.bind(widget);

        widget.serializeValue = (...args) => {
          const rawValue = originalSerializeValue
            ? originalSerializeValue(...args)
            : widget.value;

          return applyTextReplacements(
            app.graph,
            typeof rawValue === "string" ? rawValue : "",
          );
        };

        return result;
      };

      return;
    }

    const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

    nodeType.prototype.onNodeCreated = function () {
      const result = originalOnNodeCreated
        ? originalOnNodeCreated.apply(this, arguments)
        : undefined;

      if (!this.properties || !("Node name for S&R" in this.properties)) {
        this.addProperty("Node name for S&R", this.constructor.type, "string");
      }

      return result;
    };
  },
});