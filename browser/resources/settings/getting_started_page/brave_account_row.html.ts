/* Copyright (c) 2024 The Brave Authors. All rights reserved.
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at https://mozilla.org/MPL/2.0/. */

import { html, nothing } from '//resources/lit/v3_0/lit.rollup.js'

import { SettingsBraveAccountRowElement } from './brave_account_row.js'

export function getHtml(this: SettingsBraveAccountRowElement) {
  return html`
    <div class="row-container">
      ${this.state === undefined
        ? nothing
        : this.isLoggedIn_()
          ? html`
              <div class="first-row">
                <div class="circle">
                  <leo-icon name="social-brave-release-favicon-fullheight-color">
                  </leo-icon>
                </div>
                <div class="title-and-description">
                  <div class="title">${this.getLoggedInTitle_()}</div>
                  <div class="description">
                    <div id="email">${this.getLoggedInEmail_()}</div>
                  </div>
                </div>
                <leo-button kind="outline"
                            size="small"
                            @click=${this.onLogOutButtonClicked}>
                  ${this.getLogOutButtonLabel_()}
                </leo-button>
              </div>
            `
          : this.isVerification_()
            ? html`
                <div class="first-row">
                  <div class="circle">
                    <leo-icon name="social-brave-release-favicon-fullheight-color">
                    </leo-icon>
                  </div>
                  <div class="title-and-description">
                    <div class="title">${this.getVerificationRowTitle_()}</div>
                    <div class="description">
                      <localized-link
                          .localizedString=${this.getVerificationDescription_()}
                          @link-clicked=${this.onResendConfirmationEmailLinkClicked}>
                      </localized-link>
                    </div>
                  </div>
                </div>
                <div class="second-row">
                  <leo-button kind="plain"
                              size="small"
                              @click=${this.openBraveAccountDialog}>
                    ${this.getEnterRegistrationCodeButtonLabel_()}
                  </leo-button>
                  <leo-button kind="plain"
                              size="small"
                              class="cancel-registration-button"
                              @click=${this.onCancelRegistrationButtonClicked}>
                    ${this.getCancelRegistrationButtonLabel_()}
                  </leo-button>
                </div>
              `
            : html`
                <div class="first-row">
                  <div class="circle">
                    <leo-icon name="social-brave-release-favicon-fullheight-color">
                    </leo-icon>
                  </div>
                  <div class="title-and-description">
                    <div class="title">${this.getLoggedOutRowTitle_()}</div>
                    <div class="description">
                      ${this.getLoggedOutDescription_()}
                    </div>
                  </div>
                  <leo-button kind="filled"
                              size="small"
                              @click=${this.openBraveAccountDialog}>
                    ${this.getGetStartedButtonLabel_()}
                  </leo-button>
                </div>
              `
      }
    </div>`
}
