from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mods.votekick.mod_votekick import Votekick

def timer_vote_verdict(uplink: 'Votekick', channel: str) -> None:

    dnickname = uplink.Config.SERVICE_NICKNAME

    if not uplink.VoteKickManager.is_vote_ongoing(channel):
        return None
    
    votec = uplink.VoteKickManager.get_vote_channel_model(channel)
    if votec:
        target_user = uplink.User.get_nickname(votec.target_user)

        if votec.vote_for >= votec.vote_against and votec.vote_for != 0:
            uplink.Protocol.send_priv_msg(nick_from=dnickname, 
                                msg=f"User {uplink.Config.COLORS.bold}{target_user}{uplink.Config.COLORS.nogc} has {votec.vote_against} votes against and {votec.vote_for} votes for. For this reason, it\'ll be kicked from the channel",
                                channel=channel
                                )
            uplink.Protocol.send2socket(f":{dnickname} KICK {channel} {target_user} Following the vote, you are not welcome in {channel}")
        else:
            uplink.Protocol.send_priv_msg(
                    nick_from=dnickname, 
                    msg=f"User {uplink.Config.COLORS.bold}{target_user}{uplink.Config.COLORS.nogc} has {votec.vote_against} votes against and {votec.vote_for} votes for. For this reason, it\'ll remain in the channel",
                    channel=channel
                    )
        
        if uplink.VoteKickManager.init_vote_system(channel):
            uplink.Protocol.send_priv_msg(
                    nick_from=dnickname, 
                    msg="System vote re initiated",
                    channel=channel
                    )
        
        return None

    return None