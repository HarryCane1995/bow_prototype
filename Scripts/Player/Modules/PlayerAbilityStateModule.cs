using Godot;
using System;
using System.Collections.Generic;
using System.Text;

/// <summary>
/// Список игровых состояний/способностей, которые могут запрашивать authority над каналами управления игрока.
/// </summary>
public enum PlayerAbilityTag
{
    None,
    DefaultMovement,
    Crouch,
    Slide,
    SlingshotGrapplePull,
    SlingshotGrappleLaunch,
    WallRun,
    Parry,
    PrecisionStance,
    Knockback,
    Death
}

/// <summary>
/// Набор каналов управления, которые временно может занимать активная способность.
/// </summary>
[Flags]
public enum PlayerAbilityLock
{
    None = 0,
    MovementInput = 1 << 0,
    HorizontalVelocity = 1 << 1,
    VerticalVelocity = 1 << 2,
    Jump = 1 << 3,
    DoubleJump = 1 << 4,
    Slide = 1 << 5,
    Grapple = 1 << 6,
    Shooting = 1 << 7,
    LookInput = 1 << 8,
    FovControl = 1 << 9
}

/// <summary>
/// Арбитражный слой игрока: хранит активные ability-запросы, их приоритеты и lock-флаги, но не реализует сами механики.
/// </summary>
public partial class PlayerAbilityStateModule : Node
{
    /// <summary>
    /// Приоритет обычного движения по умолчанию.
    /// </summary>
    public const int PriorityDefaultMovement = 0;

    /// <summary>
    /// Приоритет crouch-состояния.
    /// </summary>
    public const int PriorityCrouch = 10;

    /// <summary>
    /// Приоритет slide: выше обычного движения, ниже будущего wall run и grapple.
    /// </summary>
    public const int PrioritySlide = 30;

    /// <summary>
    /// Зарезервированный приоритет будущего wall run.
    /// </summary>
    public const int PriorityWallRun = 40;

    /// <summary>
    /// Приоритет фазы притяжения slingshot grapple.
    /// </summary>
    public const int PrioritySlingshotGrapplePull = 60;

    /// <summary>
    /// Приоритет фазы launch slingshot grapple.
    /// </summary>
    public const int PrioritySlingshotGrappleLaunch = 65;

    /// <summary>
    /// Зарезервированный приоритет будущего parry.
    /// </summary>
    public const int PriorityParry = 70;

    /// <summary>
    /// Зарезервированный приоритет будущего knockback.
    /// </summary>
    public const int PriorityKnockback = 90;

    /// <summary>
    /// Зарезервированный максимальный приоритет death-state.
    /// </summary>
    public const int PriorityDeath = 100;

    private readonly Dictionary<PlayerAbilityTag, AbilityStateRequest> _activeRequests = new();
    private PlayerController _player;

    /// <summary>
    /// Инициализирует модуль и сохраняет ссылку на PlayerController только для будущих debug/контекстных сценариев.
    /// </summary>
    public void Initialize(PlayerController player)
    {
        _player = player;
    }

    /// <summary>
    /// Добавляет или обновляет активный ability request с указанным приоритетом, lock-флагами и именем владельца.
    /// </summary>
    public bool BeginAbility(PlayerAbilityTag tag, int priority, PlayerAbilityLock locks, string ownerName = "")
    {
        if (tag == PlayerAbilityTag.None)
        {
            return false;
        }

        _activeRequests[tag] = new AbilityStateRequest
        {
            Tag = tag,
            Priority = priority,
            Locks = locks,
            OwnerName = ownerName ?? string.Empty,
            StartedAtTime = GetNowSeconds()
        };

        return true;
    }

    /// <summary>
    /// Завершает активный request по тегу; если ownerName указан, снимает только request того же владельца.
    /// </summary>
    public void EndAbility(PlayerAbilityTag tag, string ownerName = "")
    {
        if (!_activeRequests.TryGetValue(tag, out AbilityStateRequest request))
        {
            return;
        }

        if (!string.IsNullOrEmpty(ownerName) && request.OwnerName != ownerName)
        {
            return;
        }

        _activeRequests.Remove(tag);
    }

    /// <summary>
    /// Возвращает true, если ability с указанным тегом сейчас активна.
    /// </summary>
    public bool IsAbilityActive(PlayerAbilityTag tag)
    {
        return _activeRequests.ContainsKey(tag);
    }

    /// <summary>
    /// Возвращает true, если хотя бы один активный request держит любой из указанных lock-флагов.
    /// </summary>
    public bool IsLocked(PlayerAbilityLock lockFlag)
    {
        if (lockFlag == PlayerAbilityLock.None)
        {
            return false;
        }

        foreach (AbilityStateRequest request in _activeRequests.Values)
        {
            if ((request.Locks & lockFlag) != PlayerAbilityLock.None)
            {
                return true;
            }
        }

        return false;
    }

    /// <summary>
    /// Возвращает false, если любой из requiredFreeLocks уже занят активным request.
    /// </summary>
    public bool CanStart(PlayerAbilityLock requiredFreeLocks)
    {
        return !IsLocked(requiredFreeLocks);
    }

    /// <summary>
    /// Проверяет, может ли requesterTag писать в channel: канал свободен или занят самым приоритетным request того же тега.
    /// </summary>
    public bool CanWrite(PlayerAbilityTag requesterTag, PlayerAbilityLock channel)
    {
        if (channel == PlayerAbilityLock.None)
        {
            return true;
        }

        if (!TryGetHighestPriorityRequestForLock(channel, out AbilityStateRequest request))
        {
            return true;
        }

        return request.Tag == requesterTag;
    }

    /// <summary>
    /// Возвращает тег активной способности с максимальным приоритетом или None, если активных request нет.
    /// </summary>
    public PlayerAbilityTag GetHighestPriorityAbility()
    {
        return TryGetHighestPriorityRequest(out AbilityStateRequest request) ? request.Tag : PlayerAbilityTag.None;
    }

    /// <summary>
    /// Возвращает компактную read-only строку для debug UI/logs: highest ability, aggregate locks и список request.
    /// </summary>
    public string GetDebugState()
    {
        StringBuilder builder = new();
        PlayerAbilityLock activeLocks = GetActiveLocks();

        builder.Append("Highest=");
        builder.Append(GetHighestPriorityAbility());
        builder.Append("; Locks=");
        builder.Append(activeLocks);

        if (_activeRequests.Count == 0)
        {
            builder.Append("; Requests=<none>");
            return builder.ToString();
        }

        builder.Append("; Requests=");
        bool first = true;
        foreach (AbilityStateRequest request in _activeRequests.Values)
        {
            if (!first)
            {
                builder.Append(" | ");
            }

            builder.Append(request.Tag);
            builder.Append("(p=");
            builder.Append(request.Priority);
            builder.Append(", locks=");
            builder.Append(request.Locks);
            if (!string.IsNullOrEmpty(request.OwnerName))
            {
                builder.Append(", owner=");
                builder.Append(request.OwnerName);
            }

            builder.Append(')');
            first = false;
        }

        return builder.ToString();
    }

    private bool TryGetHighestPriorityRequest(out AbilityStateRequest highestRequest)
    {
        highestRequest = default;
        bool found = false;

        foreach (AbilityStateRequest request in _activeRequests.Values)
        {
            if (!found || IsHigherPriority(request, highestRequest))
            {
                highestRequest = request;
                found = true;
            }
        }

        return found;
    }

    private bool TryGetHighestPriorityRequestForLock(PlayerAbilityLock channel, out AbilityStateRequest highestRequest)
    {
        highestRequest = default;
        bool found = false;

        foreach (AbilityStateRequest request in _activeRequests.Values)
        {
            if ((request.Locks & channel) == PlayerAbilityLock.None)
            {
                continue;
            }

            if (!found || IsHigherPriority(request, highestRequest))
            {
                highestRequest = request;
                found = true;
            }
        }

        return found;
    }

    private PlayerAbilityLock GetActiveLocks()
    {
        PlayerAbilityLock locks = PlayerAbilityLock.None;
        foreach (AbilityStateRequest request in _activeRequests.Values)
        {
            locks |= request.Locks;
        }

        return locks;
    }

    private static bool IsHigherPriority(AbilityStateRequest candidate, AbilityStateRequest current)
    {
        if (candidate.Priority != current.Priority)
        {
            return candidate.Priority > current.Priority;
        }

        return candidate.StartedAtTime >= current.StartedAtTime;
    }

    private double GetNowSeconds()
    {
        return Time.GetTicksMsec() / 1000.0;
    }

    private struct AbilityStateRequest
    {
        public PlayerAbilityTag Tag;
        public int Priority;
        public PlayerAbilityLock Locks;
        public string OwnerName;
        public double StartedAtTime;
    }
}
