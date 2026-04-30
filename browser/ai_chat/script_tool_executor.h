// Copyright (c) 2025 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#ifndef BRAVE_BROWSER_AI_CHAT_SCRIPT_TOOL_EXECUTOR_H_
#define BRAVE_BROWSER_AI_CHAT_SCRIPT_TOOL_EXECUTOR_H_

#include <string>

#include "base/memory/weak_ptr.h"
#include "brave/components/ai_chat/content/browser/associated_web_contents_content.h"
#include "chrome/common/actor.mojom-forward.h"
#include "chrome/common/chrome_render_frame.mojom.h"
#include "mojo/public/cpp/bindings/associated_remote.h"

namespace content {
class RenderFrameHost;
}

namespace ai_chat {

// Chrome-layer implementation of ScriptToolExecutionDelegate. Routes script
// tool invocations to the renderer via chrome::mojom::ChromeRenderFrame.
class ScriptToolExecutor
    : public AssociatedWebContentsContent::ScriptToolExecutionDelegate {
 public:
  ScriptToolExecutor();
  ~ScriptToolExecutor() override;

  ScriptToolExecutor(const ScriptToolExecutor&) = delete;
  ScriptToolExecutor& operator=(const ScriptToolExecutor&) = delete;

  // ScriptToolExecutionDelegate:
  void ExecuteScriptTool(content::RenderFrameHost* rfh,
                         const std::string& name,
                         const std::string& input_json,
                         ExecuteScriptToolCallback callback) override;

 private:
  void OnToolInvoked(ExecuteScriptToolCallback callback,
                     actor::mojom::ActionResultPtr result);

  mojo::AssociatedRemote<chrome::mojom::ChromeRenderFrame> render_frame_;

  base::WeakPtrFactory<ScriptToolExecutor> weak_ptr_factory_{this};
};

}  // namespace ai_chat

#endif  // BRAVE_BROWSER_AI_CHAT_SCRIPT_TOOL_EXECUTOR_H_
