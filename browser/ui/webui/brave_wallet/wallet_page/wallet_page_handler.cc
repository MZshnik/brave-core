// Copyright (c) 2026 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

#include "brave/browser/ui/webui/brave_wallet/wallet_page/wallet_page_handler.h"

#include <utility>

#include "base/notreached.h"

#if defined(TOOLKIT_VIEWS)
#include "brave/browser/ui/browser_commands.h"
#include "chrome/browser/ui/browser_finder.h"
#endif

WalletPageHandler::WalletPageHandler(
    mojo::PendingReceiver<brave_wallet::mojom::PageHandler> receiver,
    Profile* profile)
    : profile_(profile),
      receiver_(this, std::move(receiver)),
      weak_ptr_factory_(this) {}

WalletPageHandler::~WalletPageHandler() = default;

void WalletPageHandler::ShowApprovePanelUI() {
#if defined(TOOLKIT_VIEWS)
  Browser* browser = chrome::FindBrowserWithProfile(profile_);
  if (browser) {
    brave::ShowApproveWalletBubble(browser);
  }
#endif
}

void WalletPageHandler::ShowWalletBackupUI() {
  NOTREACHED();
}

void WalletPageHandler::UnlockWalletUI() {
  NOTREACHED();
}

void WalletPageHandler::ShowOnboarding(bool is_new_wallet) {
  // iOS/Mobile only
  NOTREACHED();
}

void WalletPageHandler::OpenWalletHome() {
  // iOS/Mobile only
  NOTREACHED();
}
