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
    const $insidePanel = $('#state-inside');
    const $notification = $('#notification');
    const $btnEntry    = $('#btn-entry');
    const $btnExit     = $('#btn-exit');
    const $btnPickup   = $('#btn-pickup');
    const $userName    = $('#user-name');
    const $userPhone   = $('#user-phone');
    const $parcelsList = $('#parcels-list');
    const $noParcels   = $('#no-parcels');

    /* ============ 状态 ============ */
    let currentUser = null;        // { id, name, phone, is_active, created_at }
    let activeParcels = [];       // [{ id, tracking_no, company, cabinet_number, status, ... }]
    let notifTimer = null;
    const NOTIF_DURATION = 3500;

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

    /* ============ 页面状态切换 ============ */
    function showState(state) {
        if (state === 'idle') {
            $idlePanel.style.display = 'flex';
            $insidePanel.style.display = 'none';
            currentUser = null;
            activeParcels = [];
        } else if (state === 'inside') {
            $idlePanel.style.display = 'none';
            $insidePanel.style.display = 'flex';
        }
    }

    /* ============ 渲染 ============ */
    function renderUser(user) {
        $userName.textContent = user.name || '--';
        $userPhone.textContent = user.phone || '--';
    }

    function renderParcels(parcels) {
        if (!parcels || parcels.length === 0) {
            $parcelsList.innerHTML = '';
            $noParcels.style.display = 'block';
            return;
        }
        $noParcels.style.display = 'none';
        $parcelsList.innerHTML = parcels.map(function(p) {
            return '<div class="parcel-item" data-tracking="' + p.tracking_no + '">' +
                '<div class="parcel-meta">' +
                    '<span class="parcel-company">' + (p.company || '--') + '</span>' +
                    '<span class="parcel-tracking">' + (p.tracking_no || '--') + '</span>' +
                '</div>' +
                '<div class="parcel-cabinet">' +
                    '<span class="cabinet-label">取件码</span>' +
                    '<span class="cabinet-code">' + (p.cabinet_number || '--') + '</span>' +
                '</div>' +
            '</div>';
        }).join('');
    }

    function markParcelAsPicked(trackingNo) {
        var items = $$('.parcel-item', $parcelsList);
        for (var i = 0; i < items.length; i++) {
            if (items[i].dataset.tracking === trackingNo) {
                items[i].classList.add('picked');
                var cabinetEl = $('.cabinet-code', items[i]);
                if (cabinetEl) cabinetEl.textContent = '已取件';
                break;
            }
        }
    }

    /* ============ 进门 ============ */
    async function handleEntry() {
        setBtnLoading($btnEntry, true);
        try {
            var resp = await fetch('/api/client/access/entry', { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok) {
                showNotification(json.detail || json.message || '进门验证失败', 'error');
                return;
            }

            if (json.code !== 200 || !json.data) {
                showNotification(json.message || '验证失败', 'error');
                return;
            }

            var data = json.data;
            currentUser = data.user;
            activeParcels = data.active_parcels || [];

            renderUser(currentUser);
            renderParcels(activeParcels);
            showState('inside');

            if (activeParcels.length > 0) {
                showNotification('欢迎 ' + currentUser.name + '，您有 ' + activeParcels.length + ' 个包裹待取', 'success');
            } else {
                showNotification('欢迎 ' + currentUser.name, 'success');
            }
        } catch (e) {
            showNotification('网络异常：' + e.message, 'error');
        } finally {
            setBtnLoading($btnEntry, false);
        }
    }

    /* ============ 出门 ============ */
    async function handleExit() {
        setBtnLoading($btnExit, true);
        try {
            var resp = await fetch('/api/client/access/exit', { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok) {
                showNotification(json.detail || json.message || '出门验证失败', 'error');
                return;
            }

            if (json.code !== 200 || !json.data) {
                showNotification(json.message || '验证失败', 'error');
                return;
            }

            var data = json.data;

            if (data.has_forgotten_parcels) {
                showNotification('您还有 ' + data.active_parcels.length + ' 个包裹未取，请取走后再离开', 'warning');
                setBtnLoading($btnExit, false);
                return;
            }

            showState('idle');
            showNotification('再见，欢迎下次光临', 'success');
        } catch (e) {
            showNotification('网络异常：' + e.message, 'error');
        } finally {
            setBtnLoading($btnExit, false);
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
        doPickup('face', 0);
    }

    async function doPickup(phase, retryCount) {
        if (pickupCancelFlag) return;
        if (!currentUser || !currentUser.id) {
            showNotification('用户信息丢失，请刷新页面', 'error');
            cancelPickup();
            return;
        }

        try {
            var resp = await fetch('/api/client/confirm_pickup?user_id=' + currentUser.id, { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok) {
                showNotification(json.detail || json.message || '取件失败', 'error');
                cancelPickup();
                return;
            }

            if (json.code !== 200 || !json.data) {
                var msg = json.message || '';

                if (msg.indexOf('未检测到人脸') !== -1) {
                    if (retryCount < MAX_PICKUP_RETRIES) {
                        showNotification('未检测到人脸，请正对摄像头... (' + (retryCount + 1) + '/' + MAX_PICKUP_RETRIES + ')', 'warning');
                        pickupRetryTimer = setTimeout(function() {
                            doPickup('face', retryCount + 1);
                        }, 1500);
                        return;
                    }
                    showNotification('身份验证超时，请正对摄像头后重试', 'error');
                    cancelPickup();
                    return;
                }

                if (msg.indexOf('人脸验证失败') !== -1 || msg.indexOf('本人操作') !== -1) {
                    showNotification(msg, 'error');
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
                        pickupRetryTimer = setTimeout(function() {
                            doPickup('scan', retryCount + 1);
                        }, 1500);
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
            markParcelAsPicked(parcel.tracking_no);
            showNotification('取件成功：' + parcel.tracking_no + '  柜号：' + parcel.cabinet_number, 'success');
            cancelPickup();

            activeParcels = activeParcels.filter(function(p) {
                return p.tracking_no !== parcel.tracking_no;
            });

            if (activeParcels.length === 0) {
                renderParcels([]);
            }
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
            console.log('[WS] client connected');
            if (wsReconnectTimer) {
                clearTimeout(wsReconnectTimer);
                wsReconnectTimer = null;
            }
        };

        ws.onmessage = function(event) {
            try {
                var payload = JSON.parse(event.data);
                console.log('[WS] received:', payload);

                if (payload.type === 'HARDWARE_ACTION') {
                    var action = payload.action;
                    var msg = (payload.data && payload.data.msg) || '';

                    if (action === 'DOOR_OPEN') {
                        showNotification(msg || '门已开启', 'success');
                    } else if (action === 'FORGET_ALERT') {
                        showNotification(msg || '请注意：您有包裹未取', 'warning');
                    } else {
                        showNotification(msg || '硬件触发: ' + action, 'success');
                    }
                }
            } catch (e) {
                console.error('[WS] parse error:', e);
            }
        };

        ws.onclose = function() {
            console.log('[WS] disconnected, reconnect in 3s');
            scheduleReconnect();
        };

        ws.onerror = function() {
            console.log('[WS] error');
        };
    }

    function scheduleReconnect() {
        if (wsReconnectTimer) return;
        wsReconnectTimer = setTimeout(function() {
            wsReconnectTimer = null;
            connectWebSocket();
        }, 3000);
    }

    /* ============ 事件绑定 ============ */
    $btnEntry.addEventListener('click', handleEntry);
    $btnExit.addEventListener('click', handleExit);

    $btnPickup.addEventListener('click', function() {
        if ($btnPickup.classList.contains('cancelling')) {
            cancelPickup();
        } else {
            startPickup();
        }
    });

    /* ============ 初始化 ============ */
    showState('idle');
    connectWebSocket();
})();
