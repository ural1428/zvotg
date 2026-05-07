const tg = window.Telegram?.WebApp;

const state = {
    profile: null,
    tariffs: [],
    selectedTariff: null,
    pendingOrder: null,
    forcedRenewCerId: null,
};

if (tg) {
    tg.ready();
    tg.expand();
}

function initData() {
    return tg?.initData || "";
}

function showAlert(message) {
    if (tg) {
        tg.showAlert(message);
    } else {
        alert(message);
    }
}

async function apiGet(path) {
    const response = await fetch(path, {
        method: "GET",
        headers: {
            "X-Telegram-Init-Data": initData(),
        },
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
        throw new Error(data.message || data.error || "Ошибка запроса");
    }

    return data;
}

async function apiPost(path, payload) {
    const response = await fetch(path, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Telegram-Init-Data": initData(),
        },
        body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
        throw new Error(data.message || data.error || "Ошибка запроса");
    }

    return data;
}

function getActiveSubscriptions() {
    return (state.profile?.subscriptions || []).filter((subscription) => {
        return subscription.is_active;
    });
}

function renderProfile(profileData) {
    state.profile = profileData;

    const subscriptionTitle = document.getElementById("subscriptionTitle");
    const subscriptionText = document.getElementById("subscriptionText");
    const daysBadge = document.getElementById("daysBadge");
    const statusDot = document.getElementById("statusDot");
    const primaryAction = document.getElementById("primaryAction");

    const activeCount = profileData.profile.active_count;
    const totalCount = profileData.profile.total_count;
    const maxDaysLeft = profileData.profile.max_days_left;

    if (activeCount > 0) {
        subscriptionTitle.textContent = "Активна";
        subscriptionText.textContent = `Активных подписок: ${activeCount} из ${totalCount}`;
        daysBadge.textContent = maxDaysLeft;
        statusDot.classList.remove("inactive");
        primaryAction.textContent = "Выбрать тариф для продления";
    } else {
        subscriptionTitle.textContent = "Нет активной подписки";
        subscriptionText.textContent = "Выберите тариф ниже";
        daysBadge.textContent = "0";
        statusDot.classList.add("inactive");
        primaryAction.textContent = "Купить подписку";
    }
}

function renderSubscriptions(profileData) {
    const section = document.getElementById("subscriptionsSection");
    const list = document.getElementById("subscriptionsList");
    const count = document.getElementById("subscriptionsCount");

    const subscriptions = profileData.subscriptions || [];

    list.innerHTML = "";

    if (subscriptions.length === 0) {
        section.classList.add("hidden");
        return;
    }

    section.classList.remove("hidden");
    count.textContent = `${subscriptions.length} / 5`;

    subscriptions.forEach((subscription) => {
        const item = document.createElement("div");
        item.className = "subscription-item";

        const statusText = subscription.is_active ? "Активна" : "Не активна";
        const statusClass = subscription.is_active ? "active" : "inactive";

        const daysText = subscription.is_active
            ? `Осталось ${subscription.days_left} дн.`
            : "Срок действия истёк";

        item.innerHTML = `
            <div class="subscription-item-top">
                <div>
                    <p class="subscription-name">Подписка #${subscription.index}</p>
                    <div class="subscription-meta">
                        ${daysText}<br>
                        ID: ${subscription.cer_id}
                    </div>
                </div>

                <div class="status-pill ${statusClass}">
                    ${statusText}
                </div>
            </div>

            <div class="subscription-actions">
                ${
                    subscription.is_active
                        ? `<button class="small-button" type="button" data-renew="${subscription.cer_id}">
                               Продлить
                           </button>`
                        : `<button class="small-button secondary" type="button" disabled>
                               Недоступна
                           </button>`
                }
            </div>
        `;

        list.appendChild(item);
    });

    document.querySelectorAll("[data-renew]").forEach((button) => {
        button.addEventListener("click", () => {
            state.forcedRenewCerId = button.dataset.renew;

            document.getElementById("tariffGrid").scrollIntoView({
                behavior: "smooth",
                block: "center",
            });

            showAlert("Выберите тариф для продления подписки.");
        });
    });
}

function renderTariffs(tariffs) {
    state.tariffs = tariffs;

    const tariffGrid = document.getElementById("tariffGrid");
    tariffGrid.innerHTML = "";

    tariffs.forEach((tariff) => {
        const button = document.createElement("button");
        button.className = "tariff-card";
        button.type = "button";

        button.innerHTML = `
            <span>${tariff.title}</span>
            <b>${tariff.amount} ₽</b>
        `;

        button.addEventListener("click", () => {
            startOrderFlow(tariff);
        });

        tariffGrid.appendChild(button);
    });
}

function startOrderFlow(tariff) {
    state.selectedTariff = tariff;

    if (state.forcedRenewCerId) {
        showEmailForm({
            tariff,
            action: "renew",
            cerId: state.forcedRenewCerId,
        });

        state.forcedRenewCerId = null;
        return;
    }

    const activeSubscriptions = getActiveSubscriptions();

    if (activeSubscriptions.length === 0) {
        showEmailForm({
            tariff,
            action: "buy",
            cerId: null,
        });
        return;
    }

    if (activeSubscriptions.length === 1) {
        showEmailForm({
            tariff,
            action: "renew",
            cerId: activeSubscriptions[0].cer_id,
        });
        return;
    }

    showRenewSelector(tariff, activeSubscriptions);
}

function showRenewSelector(tariff, subscriptions) {
    const renewSection = document.getElementById("renewSection");
    const renewList = document.getElementById("renewList");

    renewList.innerHTML = "";

    subscriptions.forEach((subscription) => {
        const button = document.createElement("button");
        button.className = "action-row";
        button.type = "button";

        button.innerHTML = `
            <span>
                <span class="subscription-choice-title">
                    Подписка #${subscription.index}
                </span>
                <span class="subscription-choice-subtitle">
                    Осталось ${subscription.days_left} дн. · ${subscription.cer_id}
                </span>
            </span>
            <span class="arrow">›</span>
        `;

        button.addEventListener("click", () => {
            hideRenewSelector();

            showEmailForm({
                tariff,
                action: "renew",
                cerId: subscription.cer_id,
            });
        });

        renewList.appendChild(button);
    });

    renewSection.classList.remove("hidden");
    renewSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
}

function hideRenewSelector() {
    const renewSection = document.getElementById("renewSection");
    renewSection.classList.add("hidden");
}

async function showEmailForm({ tariff, action, cerId }) {
    state.pendingOrder = {
        tariff,
        action,
        cerId,
    };

    const emailSection = document.getElementById("emailSection");
    const emailTariffTitle = document.getElementById("emailTariffTitle");
    const emailInput = document.getElementById("emailInput");

    emailTariffTitle.textContent = `${tariff.title} · ${tariff.amount} ₽`;
    emailInput.value = "";

    emailSection.classList.remove("hidden");

    setTimeout(() => {
        emailInput.focus();
    }, 100);

    emailSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
}


function hideEmailForm() {
    const emailSection = document.getElementById("emailSection");
    emailSection.classList.add("hidden");
}


function isValidEmail(email) {
    return /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email);
}


async function createOrderFromEmail() {
    const emailInput = document.getElementById("emailInput");
    const email = emailInput.value.trim().toLowerCase();

    if (!state.pendingOrder) {
        showAlert("Не выбран тариф.");
        return;
    }

    if (!isValidEmail(email)) {
        showAlert("Введите корректный email для отправки чека.");
        return;
    }

    const { tariff, action, cerId } = state.pendingOrder;

    const payload = {
        tariff_code: tariff.code,
        action,
        email,
    };

    if (action === "renew") {
        payload.cer_id = cerId;
    }

    try {
        showLoading(true);

        const data = await apiPost("/webapp/api/orders/create", payload);

        if (data.payment_url) {
            window.location.href = data.payment_url;
        } else {
            showAlert("Банк не вернул ссылку на оплату.");
        }
    } catch (error) {
        showAlert(error.message);
    } finally {
        showLoading(false);
    }
}

function showLoading(isLoading) {
    const primaryAction = document.getElementById("primaryAction");

    if (isLoading) {
        primaryAction.disabled = true;
        primaryAction.textContent = "Подготавливаю оплату...";
        return;
    }

    primaryAction.disabled = false;

    if (state.profile?.profile?.active_count > 0) {
        primaryAction.textContent = "Выбрать тариф для продления";
    } else {
        primaryAction.textContent = "Купить подписку";
    }
}

function bindActions() {
    document.getElementById("primaryAction").addEventListener("click", () => {
        const tariffGrid = document.getElementById("tariffGrid");

        tariffGrid.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    });

    document.getElementById("cancelRenewSelect").addEventListener("click", () => {
        hideRenewSelector();
    });

    document.getElementById("payButton").addEventListener("click", () => {
        createOrderFromEmail();
    });

    document.getElementById("cancelEmailButton").addEventListener("click", () => {
        hideEmailForm();
    });

    document.getElementById("emailInput").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            createOrderFromEmail();
        }
    });

    document.querySelectorAll(".action-row").forEach((button) => {
        button.addEventListener("click", () => {
            const action = button.dataset.action;

            if (!action) {
                return;
            }

            if (action === "support") {
                showAlert("Поддержка пока доступна в основном боте.");
                return;
            }

            showAlert("Скоро здесь появится раздел.");
        });
    });
}

async function bootstrap() {
    if (!initData()) {
        document.getElementById("subscriptionTitle").textContent = "Откройте через Telegram";
        document.getElementById("subscriptionText").textContent =
            "Web App должен быть открыт из кнопки в боте.";
        document.getElementById("daysBadge").textContent = "—";
        return;
    }

    try {
        const profile = await apiGet("/webapp/api/profile");
        const tariffs = await apiGet("/webapp/api/tariffs");

        renderProfile(profile);
        renderSubscriptions(profile);
        renderTariffs(tariffs.tariffs);
        bindActions();
    } catch (error) {
        document.getElementById("subscriptionTitle").textContent = "Ошибка";
        document.getElementById("subscriptionText").textContent = error.message;
        document.getElementById("daysBadge").textContent = "!";
    }
}

bootstrap();