// Copyright (c) 2025 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#include "brave/components/ai_chat/core/browser/tools/script_tool_wrapper.h"

#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "base/functional/bind.h"
#include "base/json/json_reader.h"
#include "base/memory/weak_ptr.h"
#include "base/values.h"
#include "brave/components/ai_chat/core/browser/associated_content_delegate.h"
#include "brave/components/ai_chat/core/browser/tools/tool_utils.h"
#include "third_party/blink/public/mojom/content_extraction/script_tools.mojom.h"

namespace ai_chat {

ScriptToolWrapper::ScriptToolWrapper(
    const blink::mojom::ScriptTool& script_tool,
    base::WeakPtr<AssociatedContentDelegate> delegate)
    : delegate_(std::move(delegate)),
      name_(script_tool.name),
      description_(script_tool.description) {
  if (!script_tool.input_schema) {
    return;
  }
  auto schema = base::JSONReader::ReadDict(*script_tool.input_schema,
                                          base::JSON_PARSE_CHROMIUM_EXTENSIONS);
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

ScriptToolWrapper::~ScriptToolWrapper() = default;

std::string_view ScriptToolWrapper::Name() const {
  return name_;
}

std::string_view ScriptToolWrapper::Description() const {
  return description_;
}

std::optional<base::DictValue> ScriptToolWrapper::InputProperties() const {
  if (!input_properties_) {
    return std::nullopt;
  }
  return input_properties_->Clone();
}

std::optional<std::vector<std::string>>
ScriptToolWrapper::RequiredProperties() const {
  if (required_properties_.empty()) {
    return std::nullopt;
  }
  return required_properties_;
}

void ScriptToolWrapper::UseTool(const std::string& input_json,
                                UseToolCallback callback) {
  LOG(ERROR) << "[ScriptToolWrapper] UseTool: name=" << name_
             << " delegate=" << (delegate_ ? "valid" : "null");
  if (!delegate_) {
    std::move(callback).Run({}, {});
    return;
  }
  delegate_->ExecuteScriptTool(
      name_, input_json,
      base::BindOnce(
          [](UseToolCallback cb, std::optional<std::string> result) {
            std::move(cb).Run(
                CreateContentBlocksForText(result.value_or("")), {});
          },
          std::move(callback)));
}

}  // namespace ai_chat
