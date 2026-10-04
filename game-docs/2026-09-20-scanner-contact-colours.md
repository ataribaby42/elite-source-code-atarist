# Scanner contact colours

The Atari ST and Amiga versions use the same colours for scanner contacts.
Each colour identifies the contact's role or category.

| Colour | Meaning |
| --- | --- |
| Yellow | Traders |
| Light blue | Pirates |
| Light green | Shuttles |
| Magenta / pink | Debris |
| Medium blue | Police |
| Orange | Bounty hunters |
| Red | Missiles |
| Light grey | Alien ships |

## Flashing contacts

A flashing contact indicates that the ship is flagged as hostile towards the
player. It retains its normal category colour: for example, a hostile police
Viper flashes blue.

In the code, flashing is controlled by the ship's `angry` flag. Fighting another
AI ship does not by itself make a contact flash.

## Source references

The `blip_colours` table defines the colours, and the `radar` routine controls
flashing in both platform source trees:

- [Atari ST radar code](../src_atari/asm/radar.m68)
- [Amiga radar code](../src_amiga/asm/radar.m68)
