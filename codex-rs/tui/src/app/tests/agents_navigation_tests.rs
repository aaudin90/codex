use super::*;
use pretty_assertions::assert_eq;

#[tokio::test]
async fn configured_open_agents_key_opens_subagents_picker_and_preserves_draft() -> Result<()> {
    for (keymap_config, keys) in [
        (
            "[global]\nopen_agents = [\"alt-a\"]",
            vec![KeyEvent::new(KeyCode::Char('a'), KeyModifiers::ALT)],
        ),
        (
            "[global]\nopen_agents = [\"ctrl-x a\"]",
            vec![
                KeyEvent::new(KeyCode::Char('x'), KeyModifiers::CONTROL),
                KeyEvent::new(KeyCode::Char('a'), KeyModifiers::NONE),
            ],
        ),
    ] {
        let (mut app, mut app_events, _op_rx) = make_test_app_with_channels().await;
        app.config.features.disable(Feature::Collab)?;
        let config = toml::from_str(keymap_config)?;
        app.keymap =
            crate::keymap::RuntimeKeymap::from_config(&config).expect("valid subagent shortcuts");
        app.chat_widget.apply_keymap_update(config, &app.keymap);
        app.chat_widget
            .restore_user_message_to_composer("keep this draft".into());
        let input_before = app.chat_widget.capture_thread_input_state();
        let mut tui = crate::tui::test_support::make_test_tui()?;
        let mut app_server = crate::start_embedded_app_server_for_picker(&app.config).await?;

        for key in keys {
            app.handle_tui_event(&mut tui, &mut app_server, TuiEvent::Key(key))
                .await?;
        }

        let event = app_events.try_recv()?;
        assert_matches!(event, AppEvent::OpenAgentPicker);
        app.handle_event(&mut tui, &mut app_server, event).await?;
        assert!(app.chat_widget.has_active_view());
        assert_eq!(app.chat_widget.capture_thread_input_state(), input_before);
        assert!(render_bottom_popup(&app.chat_widget, /*width*/ 80).contains("Enable subagents?"));
        app.handle_tui_event(
            &mut tui,
            &mut app_server,
            TuiEvent::Key(KeyCode::Esc.into()),
        )
        .await?;
        assert!(!app.chat_widget.has_active_view());
        assert_eq!(app.chat_widget.capture_thread_input_state(), input_before);
        app_server.shutdown().await?;
    }
    Ok(())
}

#[tokio::test]
async fn agents_navigation_requires_local_daemon() -> Result<()> {
    let (mut app, mut events, _op_rx) = make_test_app_with_channels().await;
    let mut tui = crate::tui::test_support::make_test_tui()?;
    let mut app_server = start_config_write_test_app_server(&app).await?;
    let endpoint = crate::RemoteAppServerEndpoint::UnixSocket {
        socket_path: AbsolutePathBuf::relative_to_current_dir("codex.sock")?,
    };
    for target in [
        AppServerTarget::Embedded,
        AppServerTarget::Remote {
            endpoint: endpoint.clone(),
        },
        AppServerTarget::LocalDaemon {
            endpoint,
            allow_embedded_fallback: true,
        },
    ] {
        let enabled = matches!(target, AppServerTarget::LocalDaemon { .. });
        app.app_server_target = target;
        let init = app.chatwidget_init_for_forked_or_resumed_thread(
            &mut tui,
            app.config.clone(),
            /*initial_user_message*/ None,
        );
        app.replace_chat_widget(ChatWidget::new_with_app_event(init));
        while events.try_recv().is_ok() {}
        app.handle_tui_event(
            &mut tui,
            &mut app_server,
            TuiEvent::Key(KeyCode::Left.into()),
        )
        .await?;
        if enabled {
            let event = events.try_recv()?;
            assert_matches!(event, AppEvent::OpenAgentsOverview);
            app.handle_event(&mut tui, &mut app_server, event).await?;
            assert!(!app.chat_widget.no_modal_or_popup_active());
        } else {
            assert!(events.try_recv().is_err());
            assert!(app.chat_widget.no_modal_or_popup_active());
            assert!(!render_bottom_popup(&app.chat_widget, /*width*/ 96).contains("for agents"));
        }
    }
    app_server.shutdown().await?;
    Ok(())
}

#[tokio::test]
async fn pending_windows_sandbox_setup_blocks_thread_replacement() -> Result<()> {
    use crate::app_event::WindowsSandboxEnableMode;

    let (mut app, mut events, _ops) = make_test_app_with_channels().await;
    app.chat_widget.windows_sandbox_local_server = true;
    while events.try_recv().is_ok() {}
    let mut app_server = start_config_write_test_app_server(&app).await?;
    let mut tui = crate::tui::test_support::make_test_tui()?;
    let current = ThreadId::new();
    let other = ThreadId::new();
    app.active_thread_id = Some(current);
    app.primary_thread_id = Some(current);
    let preset = codex_utils_approval_presets::builtin_approval_presets()
        .into_iter()
        .find(|preset| preset.id == "auto")
        .expect("auto preset");
    app.windows_sandbox.pending_setup = Some((WindowsSandboxEnableMode::Elevated, preset, None));
    let prompt = crate::chatwidget::create_initial_user_message(
        Some("review this".to_string()),
        Vec::new(),
        Vec::new(),
    );
    app.chat_widget.initial_user_message = prompt.clone();

    app.select_agent_thread(&mut tui, &mut app_server, other)
        .await?;
    assert_eq!(app.active_thread_id, Some(current));
    assert_eq!(app.chat_widget.initial_user_message, prompt);
    let cell = match events.try_recv() {
        Ok(AppEvent::InsertHistoryCell(cell)) => cell,
        other => panic!("expected setup navigation message, got {other:?}"),
    };
    let rendered = lines_to_single_string(&cell.display_lines(/*width*/ 100));
    insta::assert_snapshot!(rendered, @"• Finish Windows sandbox setup before switching threads.");

    app.chat_widget.initial_user_message = None;
    app.run_agents_overview_action(
        &mut tui,
        &mut app_server,
        current,
        crate::app_event::AgentsOverviewAction::Archive,
    )
    .await?;
    assert_eq!(app.active_thread_id, Some(current));
    assert!(events.try_recv().is_err());

    app_server.shutdown().await?;
    Ok(())
}
