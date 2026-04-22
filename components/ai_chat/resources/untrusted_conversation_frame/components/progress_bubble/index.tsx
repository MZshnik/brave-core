// Copyright (c) 2026 The Brave Authors. All rights reserved.
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this file,
// You can obtain one at https://mozilla.org/MPL/2.0/.

import * as React from 'react'
import ProgressRing from '@brave/leo/react/progressRing'
import Icon from '@brave/leo/react/icon'
import classnames from '$web-common/classnames'
import { getLocale } from '$web-common/locale'
import * as Mojom from '../../../common/mojom'
import { useUntrustedConversationContext } from '../../untrusted_conversation_context'
import { getToolLabel } from '../assistant_response/get_tool_label'
import { isAssistantGroupTask } from '../conversation_entries/conversation_entries_utils'
import styles from './style.module.scss'

interface Props {
  responseGroup: Mojom.ConversationTurn[] | undefined
  isLastGroup: boolean
}

export interface ProgressBubbleContext {
  isExpanded: boolean
  setIsExpanded: (state: boolean) => void
}

const Context = React.createContext<ProgressBubbleContext>({
  isExpanded: false,
  setIsExpanded(state) {},
})

export function ProgressBubbleContextProvider(props: React.PropsWithChildren) {
  const [isExpanded, setIsExpanded] = React.useState<boolean>(false)

  return (
    <Context.Provider value={{ isExpanded, setIsExpanded }}>
      {props.children}
    </Context.Provider>
  )
}

export function useProgressBubbleContext () {
  return React.useContext(Context)
}

/**
 * Aids tracking when a sticky item is stuck, given lack of CSS support to
 * target an element only when sticky is active.
 * @param beforeRef A sentinel element positioned at the top sticky position
 * @param afterRef A sentinel element positioned at the bottom sticky position
 * @returns whether either sentinel is outside the area of intersection
 */
function useStickyState(
  beforeRef: React.RefObject<HTMLElement>,
  afterRef: React.RefObject<HTMLElement>,
) {
  const [isStuck, setIsStuck] = React.useState(false)

  React.useEffect(() => {
    const beforeEl = beforeRef.current
    const afterEl = afterRef.current
    if (!beforeEl || !afterEl) return

    const observer = new IntersectionObserver(
      (entries) => {
        let shouldBeInStuckState = false
        entries.forEach((entry) => {
          if (entry.target === beforeEl)
            shouldBeInStuckState = !entry.isIntersecting
          if (!shouldBeInStuckState && entry.target === afterEl)
            shouldBeInStuckState = !entry.isIntersecting
        })
        setIsStuck(shouldBeInStuckState)
      },
      { threshold: [0] },
    )

    observer.observe(beforeEl)
    observer.observe(afterEl)
    return () => observer.disconnect()
  }, [beforeRef, afterRef])

  return isStuck
}

export default function ProgressBubble(props: Props) {
  const conversationContext = useUntrustedConversationContext()
  const context = useProgressBubbleContext()

  const beforeSentinel = React.useRef<HTMLDivElement>(null)
  const afterSentinel = React.useRef<HTMLDivElement>(null)
  const isStuck = useStickyState(beforeSentinel, afterSentinel)

  const isGenerating = conversationContext.api.useStateData().isGenerating

  const isExpandable = props.responseGroup && isAssistantGroupTask(props.responseGroup)

  let progressText: string | null = null
  let isComplete = false

  const lastEvents = props.responseGroup?.at(-1)?.events

  const lastEvent = React.useMemo(() => {
    const events = lastEvents?.filter(event =>
      // filter out events that are not replacements for status, i.e. do not
      // have their own progress, even if we don't know the string for that
      // progress. i.e. don't filter out events that are indicitive that something
      // is happening - we don't want to show "doing A" if it's actually "doing B"
      // even if we don't have a string representation for "B".

      // Filter out events that are extra data received that might be parallel
      // to other events.
      !event.conversationTitleEvent &&
      !event.contentReceiptEvent &&
      !event.inlineSearchEvent &&

      // Filter out search status events since we get more data from the tool
      // use event.
      !event.searchQueriesEvent &&
      !event.searchStatusEvent &&
      !event.sourcesEvent
    )

    return events?.at(-1)
  }, [lastEvents])

  const toolInput = React.useMemo(() => {
    if (!lastEvent?.toolUseEvent?.argumentsJson) {
      return null
    }
    try {
      return JSON.parse(lastEvent?.toolUseEvent.argumentsJson)
    } catch (e) {
      return null
    }
  }, [lastEvent?.toolUseEvent?.argumentsJson])

  if (isGenerating && props.isLastGroup) {
    // Default to "Thinking"
    progressText = getLocale(S.CHAT_UI_TOOL_LABEL_THINKING)

    if (conversationContext.toolUseTaskState === Mojom.TaskState.kPaused) {
      progressText = getLocale(S.CHAT_UI_TASK_STATE_PAUSED_LABEL)
    }
    if (conversationContext.toolUseTaskState === Mojom.TaskState.kStopped) {
      progressText = getLocale(S.CHAT_UI_TASK_STATE_STOPPED_LABEL)
    }

    // Override with something more specific, when we can
    if (lastEvent?.toolUseEvent) {
      const toolLabel = getToolLabel(lastEvent.toolUseEvent.toolName, toolInput)
      if (toolLabel) {
        progressText = toolLabel
      }
    }
    if (lastEvent?.deepResearchEvent) {
      // TODO
    }
  } else if (isExpandable) {
    progressText = "Task complete"
    isComplete = true
  }

  if (!progressText) {
    return null
  }

  const onClickHandler = isExpandable
    ? () => {
        context.setIsExpanded(!context.isExpanded)
        // When expanding, make sure the start of the expanded content
        // is in view. This assumes that the ProgressBubble is directly above
        // the expanded/contracted content view. If that is not the case,
        // perhaps the scrollIntoView should be handled in the content's
        // component instead, reacting to context.isExpanded changing.
        beforeSentinel.current?.scrollIntoView(true)
      }
    : undefined

  return (
    <>
      <div
        ref={beforeSentinel}
        className={classnames(styles.sentinel, styles.top)}
        aria-hidden='true'
      />
      <div
        className={classnames(
          styles.bubble,
          isStuck && styles.isStuck,
          !isComplete && styles.isActive,
          isExpandable && styles.isExpandable,
        )}
        onClick={onClickHandler}
      >
        {isComplete && (
          <Icon
            className={styles.icon}
            name='check-circle-outline'
          />
        )}
        {!isComplete && <ProgressRing className={styles.icon} />}
        <span className={styles.description}>{progressText}</span>
        {isExpandable && (
          <Icon
            className={styles.expander}
            name={context.isExpanded ? 'carat-up' : 'carat-right'}
          />
        )}
      </div>
      <div
        ref={afterSentinel}
        className={classnames(styles.sentinel, styles.bottom)}
        aria-hidden='true'
      />
    </>
  )
}
