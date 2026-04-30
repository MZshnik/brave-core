// Copyright (c) 2025 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#include "brave/browser/ai_chat/script_tool_executor.h"

#include <utility>

#include "base/functional/bind.h"
#include "chrome/common/actor.mojom.h"
#include "chrome/common/actor/actor_constants.h"
#include "chrome/common/actor/task_id.h"
#include "content/public/browser/render_frame_host.h"
#include "third_party/blink/public/common/associated_interfaces/associated_interface_provider.h"

namespace ai_chat {

ScriptToolExecutor::ScriptToolExecutor() = default;
ScriptToolExecutor::~ScriptToolExecutor() = default;

void ScriptToolExecutor::ExecuteScriptTool(
    content::RenderFrameHost* rfh,
    const std::string& name,
    const std::string& input_json,
    ExecuteScriptToolCallback callback) {
  render_frame_.reset();
  rfh->GetRemoteAssociatedInterfaces()->GetInterface(&render_frame_);

  auto invocation = actor::mojom::ToolInvocation::New();
  // Use a sentinel task ID since this invocation is outside any actor task.
  invocation->task_id = actor::TaskId::FromUnsafeValue(1);
  invocation->action = actor::mojom::ToolAction::NewScriptTool(
      actor::mojom::ScriptToolAction::New(name, input_json));
  invocation->target =
      actor::mojom::ToolTarget::NewDomNodeId(actor::kRootElementDomNodeId);

  render_frame_->InvokeTool(
      std::move(invocation),
      base::BindOnce(&ScriptToolExecutor::OnToolInvoked,
                     weak_ptr_factory_.GetWeakPtr(), std::move(callback)));
}

void ScriptToolExecutor::OnToolInvoked(ExecuteScriptToolCallback callback,
                                       actor::mojom::ActionResultPtr result) {
  render_frame_.reset();
  if (result && result->code == actor::mojom::ActionResultCode::kOk &&
      result->script_tool_response && result->script_tool_response->result) {
    std::move(callback).Run(*result->script_tool_response->result);
  } else {
    std::move(callback).Run(std::nullopt);
  }
}

}  // namespace ai_chat
