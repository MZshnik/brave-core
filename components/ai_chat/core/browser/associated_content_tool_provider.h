// Copyright (c) 2025 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#ifndef BRAVE_COMPONENTS_AI_CHAT_CORE_BROWSER_ASSOCIATED_CONTENT_TOOL_PROVIDER_H_
#define BRAVE_COMPONENTS_AI_CHAT_CORE_BROWSER_ASSOCIATED_CONTENT_TOOL_PROVIDER_H_

#include <memory>
#include <vector>

#include "base/memory/weak_ptr.h"
#include "brave/components/ai_chat/core/browser/tools/tool.h"
#include "brave/components/ai_chat/core/browser/tools/tool_provider.h"

namespace ai_chat {

class AssociatedContentDelegate;

// Provides tools derived from a single piece of AssociatedContent. Currently
// wraps the ScriptTools exposed by the page via the AI Page Content API.
// Rebuilds its tool list at the start of each generation loop so that tool
// availability always reflects the latest state of the associated content.
class AssociatedContentToolProvider : public ToolProvider {
 public:
  explicit AssociatedContentToolProvider(
      base::WeakPtr<AssociatedContentDelegate> content);
  ~AssociatedContentToolProvider() override;

  AssociatedContentToolProvider(const AssociatedContentToolProvider&) = delete;
  AssociatedContentToolProvider& operator=(
      const AssociatedContentToolProvider&) = delete;

  // ToolProvider:
  void OnNewGenerationLoop() override;
  std::vector<base::WeakPtr<Tool>> GetTools() override;

 private:
  void RebuildTools();

  base::WeakPtr<AssociatedContentDelegate> content_;
  std::vector<std::unique_ptr<Tool>> tools_;
};

}  // namespace ai_chat

#endif  // BRAVE_COMPONENTS_AI_CHAT_CORE_BROWSER_ASSOCIATED_CONTENT_TOOL_PROVIDER_H_
