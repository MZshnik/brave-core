// Copyright 2026 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import BraveCore
@_spi(ChromiumWebViewAccess) import Web

extension TabDataValues {
  private struct RequestBlockingTabHelperKey: TabDataKey {
    static var defaultValue: RequestBlockingTabHelper?
  }
  public var requestBlockingTabHelper: RequestBlockingTabHelper? {
    get { self[RequestBlockingTabHelperKey.self] }
    set { self[RequestBlockingTabHelperKey.self] = newValue }
  }
}

public class RequestBlockingTabHelper: TabObserver {

  private weak var tab: (any TabState)?
  private let delegate = RequestBlockingJavaScriptFeatureDelegate()

  public init(tab: some TabState) {
    self.tab = tab
    tab.addObserver(self)
  }

  // MARK: - TabObserver

  public func tabDidCreateWebView(_ tab: some TabState) {
    BraveWebView.from(tab: tab)?.setRequestBlockingDelegate(delegate)
  }

  public func tabWillBeDestroyed(_ tab: some TabState) {
    tab.removeObserver(self)
  }
}

private class RequestBlockingJavaScriptFeatureDelegate: NSObject, RequestBlockingDelegate {

  override init() {

  }

  func adblockMode(_ requestURL: URL) -> BraveShields.AdBlockMode {
    return .standard
  }

  func shouldBlock(
    requestURL: URL,
    sourceURL: URL,
    resourceType: String,
    adblockMode: BraveShields.AdBlockMode
  ) -> Bool {
    return false
  }
}
