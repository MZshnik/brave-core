// Copyright (c) 2025 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#include "brave/components/ai_chat/core/browser/associated_content_tool_provider.h"

#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "base/json/json_reader.h"
#include "base/memory/weak_ptr.h"
#include "base/values.h"
#include "brave/components/ai_chat/core/browser/associated_content_delegate.h"
#include "brave/components/ai_chat/core/browser/tools/tool.h"
#include "third_party/blink/public/mojom/content_extraction/script_tools.mojom.h"

namespace ai_chat {

namespace {

// Wraps a blink::mojom::ScriptTool as a Tool so it can be included in a
// conversation's tool list.
class ScriptToolWrapper : public Tool {
 public:
  explicit ScriptToolWrapper(const blink::mojom::ScriptTool& script_tool)
      : name_(script_tool.name), description_(script_tool.description) {
    if (!script_tool.input_schema) {
      return;
    }
    auto schema = base::JSONReader::ReadDict(
        *script_tool.input_schema, base::JSON_PARSE_CHROMIUM_EXTENSIONS);
    if (!schema) {
      return;
    }
    if (auto* props = schema->FindDict("properties")) {
      input_properties_ = props->Clone();
    }
    if (auto* required = schema->FindList("required")) {
      for (const auto& item : *required) {
        if (item.is_string()) {
          required_properties_.push_back(item.GetString());
        }
      }
    }
  }

  ~ScriptToolWrapper() override = default;

  std::string_view Name() const override { return name_; }
  std::string_view Description() const override { return description_; }

  std::optional<base::DictValue> InputProperties() const override {
    if (!input_properties_) {
      return std::nullopt;
    }
    return input_properties_->Clone();
  }

  std::optional<std::vector<std::string>> RequiredProperties() const override {
    if (required_properties_.empty()) {
      return std::nullopt;
    }
    return required_properties_;
  }

  void UseTool(const std::string& input_json,
               UseToolCallback callback) override {
    // TODO(https://github.com/brave/brave-browser/issues/XXXXX):
    // Route invocation back to the renderer via ScriptToolHost.
    std::move(callback).Run({}, {});
  }

 private:
  std::string name_;
  std::string description_;
  std::optional<base::DictValue> input_properties_;
  std::vector<std::string> required_properties_;
};

}  // namespace

AssociatedContentToolProvider::AssociatedContentToolProvider(
    base::WeakPtr<AssociatedContentDelegate> content)
    : content_(std::move(content)) {
  RebuildTools();
}

AssociatedContentToolProvider::~AssociatedContentToolProvider() = default;

void AssociatedContentToolProvider::OnNewGenerationLoop() {
  RebuildTools();
}

std::vector<base::WeakPtr<Tool>> AssociatedContentToolProvider::GetTools() {
  std::vector<base::WeakPtr<Tool>> tool_ptrs;
  tool_ptrs.reserve(tools_.size());
  for (const auto& tool : tools_) {
    tool_ptrs.push_back(tool->GetWeakPtr());
  }
  return tool_ptrs;
}

void AssociatedContentToolProvider::RebuildTools() {
  tools_.clear();
  if (!content_) {
    return;
  }
  for (const auto& script_tool : content_->script_tools()) {
    tools_.push_back(std::make_unique<ScriptToolWrapper>(*script_tool));
  }
}

}  // namespace ai_chat
