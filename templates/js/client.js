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
    const $pickupModal = $('#pickup-modal');
    const $notification = $('#notification');
    const $btnEntry    = $('#btn-entry');
    const $btnExit     = $('#btn-exit');
    const $btnPickup   = $('#btn-pickup');
    const $btnClosePickup = $('#btn-close-pickup');
    const $userName    = $('#user-name');
    const $userPhone   = $('#user-phone');
    const $parcelsList = $('#parcels-list');
    const $noParcels   = $('#no-parcels');
    const $pickupTitle = $('#pickup-title');
    const $pickupMessage = $('#pickup-message');
    const $pickupLoading = $('#pickup-loading');

    /* ============ 状态 ============ */
    let currentUser = null;        // { id, name, phone, is_active, created_at }
    let activeParcels = [];       // [{ id, tracking_no, company, cabinet_number, status, ... }]
    let pickupInProgress = false;
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
    function openPickupModal() {
        $pickupModal.style.display = 'flex';
        $pickupTitle.textContent = '正在扫描...';
        $pickupMessage.textContent = '请将包裹二维码对准摄像头';
        $pickupLoading.style.display = 'block';
        $btnClosePickup.style.display = 'none';
        pickupInProgress = false;
        doPickup();
    }

    function closePickupModal() {
        $pickupModal.style.display = 'none';
    }

    async function doPickup() {
        if (pickupInProgress) return;
        if (!currentUser || !currentUser.id) {
            showPickupResult('error', '用户信息丢失，请刷新页面');
            return;
        }

        pickupInProgress = true;
        try {
            var resp = await fetch('/api/client/confirm_pickup?user_id=' + currentUser.id, { method: 'POST' });
            var json = await resp.json();

            if (!resp.ok) {
                showPickupResult('error', json.detail || json.message || '取件失败');
                return;
            }

            if (json.code !== 200 || !json.data) {
                showPickupResult('error', json.message || '未检测到包裹二维码');
                return;
            }

            var parcel = json.data;
            markParcelAsPicked(parcel.tracking_no);
            showPickupResult('success', '取件成功：' + parcel.tracking_no + '\n柜号：' + parcel.cabinet_number);

            activeParcels = activeParcels.filter(function(p) {
                return p.tracking_no !== parcel.tracking_no;
            });
        } catch (e) {
            showPickupResult('error', '网络异常：' + e.message);
        } finally {
            pickupInProgress = false;
        }
    }

    function showPickupResult(type, msg) {
        $pickupLoading.style.display = 'none';
        $btnClosePickup.style.display = 'inline-block';
        if (type === 'success') {
            $pickupTitle.textContent = '取件成功';
            $pickupMessage.innerHTML = msg.replace(/\n/g, '<br>');
            $pickupMessage.style.color = '#16a34a';
        } else {
            $pickupTitle.textContent = '扫描失败';
            $pickupMessage.textContent = msg;
            $pickupMessage.style.color = '#dc2626';
            $btnClosePickup.textContent = '重试';
        }
    }

    function retryPickup() {
        $pickupTitle.textContent = '正在扫描...';
        $pickupMessage.textContent = '请将包裹二维码对准摄像头';
        $pickupMessage.style.color = '#94a3b8';
        $pickupLoading.style.display = 'block';
        $btnClosePickup.style.display = 'none';
        $btnClosePickup.textContent = '关闭';
        doPickup();
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
    $btnPickup.addEventListener('click', openPickupModal);

    $btnClosePickup.addEventListener('click', function() {
        if ($btnClosePickup.textContent === '重试') {
            retryPickup();
        } else {
            closePickupModal();
        }
    });

    /* 点击蒙层关闭取件弹窗 */
    $pickupModal.addEventListener('click', function(e) {
        if (e.target === $pickupModal) {
            closePickupModal();
        }
    });

    /* ============ 初始化 ============ */
    showState('idle');
    connectWebSocket();
})();
