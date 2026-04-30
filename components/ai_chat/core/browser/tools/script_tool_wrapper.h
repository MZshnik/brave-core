// Copyright (c) 2025 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#ifndef BRAVE_COMPONENTS_AI_CHAT_CORE_BROWSER_TOOLS_SCRIPT_TOOL_WRAPPER_H_
#define BRAVE_COMPONENTS_AI_CHAT_CORE_BROWSER_TOOLS_SCRIPT_TOOL_WRAPPER_H_

#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "base/memory/weak_ptr.h"
#include "base/values.h"
#include "brave/components/ai_chat/core/browser/tools/tool.h"
#include "third_party/blink/public/mojom/content_extraction/script_tools.mojom-forward.h"

namespace ai_chat {

class AssociatedContentDelegate;

// Wraps a blink::mojom::ScriptTool as a Tool so page-defined script tools
// can be included in a conversation's tool list.
class ScriptToolWrapper : public Tool {
 public:
  ScriptToolWrapper(const blink::mojom::ScriptTool& script_tool,
                    base::WeakPtr<AssociatedContentDelegate> delegate);
  ~ScriptToolWrapper() override;

  ScriptToolWrapper(const ScriptToolWrapper&) = delete;
  ScriptToolWrapper& operator=(const ScriptToolWrapper&) = delete;

  // Tool overrides:
  std::string_view Name() const override;
  std::string_view Description() const override;
  std::optional<base::DictValue> InputProperties() const override;
  std::optional<std::vector<std::string>> RequiredProperties() const override;
  void UseTool(const std::string& input_json,
               UseToolCallback callback) override;

 private:
  base::WeakPtr<AssociatedContentDelegate> delegate_;
  std::string name_;
  std::string description_;
  std::optional<base::DictValue> input_properties_;
  std::vector<std::string> required_properties_;
};

}  // namespace ai_chat

#endif  // BRAVE_COMPONENTS_AI_CHAT_CORE_BROWSER_TOOLS_SCRIPT_TOOL_WRAPPER_H_
