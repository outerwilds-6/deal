(function() {
    /* ============ 工具函数 ============ */
    function $(selector, parent) {
        return (parent || document).querySelector(selector);
    }

    function $$(selector, parent) {
        return Array.from((parent || document).querySelectorAll(selector));
    }

    /* ============ DOM 引用 ============ */
    const $idlePanel   = $('#state-idle');
    const $authPopup   = $('#auth-popup');
    const $popupTitle  = $('#popup-title');
    const $popupBody   = $('#popup-body');
    const $popupFooter = $('#popup-footer');
    const $notification = $('#notification');
    const $btnAuth     = $('#btn-auth');
    const $btnPickup   = $('#btn-pickup');

    /* ============ 常量 ============ */
    let notifTimer = null;
    const NOTIF_DURATION = 3500;
    let popupDismissTimer = null;
    const POPUP_AUTO_DISMISS = 8000;

    /* ============ 通知系统 ============ */
    function showNotification(msg, type) {
        if (notifTimer) clearTimeout(notifTimer);
        $notification.textContent = msg;
        $notification.className = 'notification ' + type + ' show';
        notifTimer = setTimeout(function() {
            $notification.className = 'notification';
        }, NOTIF_DURATION);
    }

    /* ============ 按钮加载态 ============ */
    function setBtnLoading(btn, loading) {
        if (loading) {
            btn.disabled = true;
            btn.classList.add('btn-loading');
            btn.dataset.originalText = btn.textContent;
        } else {
            btn.disabled = false;
            btn.classList.remove('btn-loading');
            if (btn.dataset.originalText) {
                btn.textContent = btn.dataset.originalText;
                delete btn.dataset.originalText;
            }
        }
    }

    /* ============ 弹窗控制 ============ */
    function showPopup() {
        $idlePanel.style.display = 'none';
        $authPopup.style.display = 'flex';
    }

    function dismissPopup() {
        if (popupDismissTimer) clearTimeout(popupDismissTimer);
        popupDismissTimer = null;
        $authPopup.style.display = 'none';
        $idlePanel.style.display = 'flex';
    }

    function startPopupAutoDismiss() {
        if (popupDismissTimer) clearTimeout(popupDismissTimer);
        popupDismissTimer = setTimeout(dismissPopup, POPUP_AUTO_DISMISS);
    }

    /* ============ 渲染 ============ */
    function renderParcelList(parcels) {
        if (!parcels || parcels.length === 0) {
            return '<p class="popup-empty">暂无在库包裹</p>';
        }
        return '<div class="popup-parcels">' + parcels.map(function(p) {
            return '<div class="pp-item">' +
                '<div class="pp-meta">' +
                    '<span class="pp-company">' + (p.company || '--') + '</span>' +
                    '<span class="pp-tracking">' + (p.tracking_no || '--') + '</span>' +
                '</div>' +
                '<div class="pp-cabinet">' +
                    '<span class="pp-cabinet-label">柜号</span>' +
                    '<span class="pp-cabinet-code">' + (p.cabinet_number || '--') + '</span>' +
                '</div>' +
            '</div>';
        }).join('') + '</div>';
    }

    /* ============ 刷脸认证（入口/出口统一） ============ */
    async function handleAuth() {
        setBtnLoading($btnAuth, true);
        try {
            var resp = await fetch('/api/client/access/auth', { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok || json.code !== 200 || !json.data) {
                showNotification(json.message || '认证失败', 'error');
                return;
            }

            var data = json.data;
            if (data.action === 'ENTRY') {
                showEntryPopup(data);
            } else if (data.action === 'EXIT') {
                showExitPopup(data);
            }
        } catch (e) {
            showNotification('网络异常：' + e.message, 'error');
        } finally {
            setBtnLoading($btnAuth, false);
        }
    }

    function showEntryPopup(data) {
        var user = data.user;
        var parcels = data.active_parcels || [];

        $popupTitle.textContent = '欢迎 ' + user.name;
        $popupBody.innerHTML = renderParcelList(parcels);
        $popupFooter.innerHTML = '<span class="popup-hint">点击任意位置关闭 · ' + (POPUP_AUTO_DISMISS / 1000) + 's 后自动关闭</span>';

        showPopup();
        startPopupAutoDismiss();
    }

    function showExitPopup(data) {
        var user = data.user;
        var expected = data.exit_expected_total || 0;
        var picked = data.exit_picked_count || 0;
        var missing = data.active_parcels || [];
        var missingCount = missing.length;

        $popupTitle.textContent = user.name + ' 请确认取件';

        var bodyHtml = '<div class="exit-stats">' +
            '<div class="exit-stat"><span class="es-label">应取</span><span class="es-value">' + expected + '</span></div>' +
            '<div class="exit-stat"><span class="es-label">已取</span><span class="es-value" style="color:var(--success)">' + picked + '</span></div>' +
            '<div class="exit-stat"><span class="es-label">未取</span><span class="es-value" style="color:' + (missingCount > 0 ? 'var(--warning)' : 'var(--success)') + '">' + missingCount + '</span></div>' +
            '</div>';

        if (missingCount > 0) {
            bodyHtml += '<p class="exit-warning">您还有 ' + missingCount + ' 个包裹未取走</p>';
            bodyHtml += renderParcelList(missing);
        } else {
            bodyHtml += '<p class="exit-ok">全部包裹已取走 ✓</p>';
        }

        $popupBody.innerHTML = bodyHtml;
        $popupFooter.innerHTML = '<div class="popup-actions">' +
            '<button id="btn-exit-confirm" class="btn btn-primary">确认离开</button>' +
            '<button id="btn-exit-back" class="btn btn-outline">我再看看</button>' +
            '</div>';

        showPopup();

        $('#btn-exit-confirm').addEventListener('click', handleExitConfirm);
        $('#btn-exit-back').addEventListener('click', dismissPopup);
    }

    async function handleExitConfirm() {
        var btn = $('#btn-exit-confirm');
        if (!btn) return;
        setBtnLoading(btn, true);
        try {
            var resp = await fetch('/api/client/access/exit_confirm', { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok || json.code !== 200) {
                showNotification(json.message || '出门失败', 'error');
                return;
            }

            showNotification('再见，欢迎下次光临', 'success');
            dismissPopup();
        } catch (e) {
            showNotification('网络异常：' + e.message, 'error');
        } finally {
            setBtnLoading(btn, false);
        }
    }

    /* ============ 取件确认 ============ */
    var pickupCancelFlag = false;
    var pickupRetryTimer = null;
    var MAX_PICKUP_RETRIES = 30;

    function cancelPickup() {
        pickupCancelFlag = true;
        if (pickupRetryTimer) clearTimeout(pickupRetryTimer);
        pickupRetryTimer = null;
        $btnPickup.textContent = '扫码取件';
        $btnPickup.classList.remove('cancelling');
    }

    function startPickup() {
        pickupCancelFlag = false;
        $btnPickup.textContent = '取消取件';
        $btnPickup.classList.add('cancelling');
        showNotification('正在人脸验证，请正对摄像头...', 'warning');
        doPickup(0);
    }

    async function doPickup(retryCount) {
        if (pickupCancelFlag) return;

        try {
            var resp = await fetch('/api/client/confirm_pickup', { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok || json.code !== 200 || !json.data) {
                var msg = json.message || '';

                if (msg.indexOf('未检测到人脸') !== -1) {
                    if (retryCount < MAX_PICKUP_RETRIES) {
                        showNotification('未检测到人脸，请正对摄像头... (' + (retryCount + 1) + '/' + MAX_PICKUP_RETRIES + ')', 'warning');
                        pickupRetryTimer = setTimeout(function() { doPickup(retryCount + 1); }, 1500);
                        return;
                    }
                    showNotification('身份验证超时，请正对摄像头后重试', 'error');
                    cancelPickup();
                    return;
                }

                if (msg.indexOf('未检测到包裹') !== -1 || msg.indexOf('二维码') !== -1) {
                    if (retryCount < MAX_PICKUP_RETRIES) {
                        if (retryCount === 0) {
                            showNotification('人脸验证通过，即将扫描二维码', 'warning');
                        } else {
                            showNotification('请将包裹二维码对准摄像头... (' + (retryCount + 1) + '/' + MAX_PICKUP_RETRIES + ')', 'warning');
                        }
                        pickupRetryTimer = setTimeout(function() { doPickup(retryCount + 1); }, 1500);
                        return;
                    }
                    showNotification('扫描超时，请确认二维码在画面中后重试', 'error');
                    cancelPickup();
                    return;
                }

                showNotification(msg, 'error');
                cancelPickup();
                return;
            }

            var parcel = json.data;
            showNotification('取件成功：' + parcel.tracking_no + '  柜号：' + parcel.cabinet_number, 'success');
            cancelPickup();
        } catch (e) {
            showNotification('网络异常：' + e.message, 'error');
            cancelPickup();
        }
    }

    /* ============ WebSocket ============ */
    var ws = null;
    var wsReconnectTimer = null;

    function connectWebSocket() {
        if (ws && ws.readyState === WebSocket.OPEN) return;

        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(protocol + '//' + window.location.host + '/ws/client');

        ws.onopen = function() {
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }
        };

        ws.onmessage = function(event) {
            try {
                var payload = JSON.parse(event.data);
                if (payload.type === 'HARDWARE_ACTION') {
                    var msg = (payload.data && payload.data.msg) || '';
                    var action = payload.action;

                    if (action === 'CABINET_UNLOCK') {
                        showNotification(msg || '柜门已解锁', 'success');
                    } else if (action === 'CABINET_LOCK') {
                        showNotification(msg || '柜门已锁闭', 'success');
                    } else if (action === 'FORGET_ALERT') {
                        showNotification(msg || '请注意：您有包裹未取', 'warning');
                    } else {
                        showNotification(msg || '硬件触发: ' + action, 'success');
                    }
                }
            } catch (e) {
                // ignore parse errors
            }
        };

        ws.onclose = function() {
            scheduleReconnect();
        };

        ws.onerror = function() {};
    }

    function scheduleReconnect() {
        if (wsReconnectTimer) return;
        wsReconnectTimer = setTimeout(function() {
            wsReconnectTimer = null;
            connectWebSocket();
        }, 3000);
    }

    /* ============ 事件绑定 ============ */
    $btnAuth.addEventListener('click', handleAuth);

    $btnPickup.addEventListener('click', function() {
        if ($btnPickup.classList.contains('cancelling')) {
            cancelPickup();
        } else {
            startPickup();
        }
    });

    $authPopup.addEventListener('click', function(e) {
        if (e.target === $authPopup) dismissPopup();
    });

    /* ============ 初始化 ============ */
    connectWebSocket();
})();
