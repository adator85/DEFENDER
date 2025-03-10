# IRC-DEFENDER
![Static Badge](https://img.shields.io/badge/UnrealIRCd-6.2.2%20or%20later-green)
![Static Badge](https://img.shields.io/badge/Python3-3.10%20or%20later-green)
![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fadator85%2FIRC_DEFENDER_MODULES%2Fmain%2Fversion.json&query=version&label=Current%20Version)
![Static Badge](https://img.shields.io/badge/Maintained-Yes-green)

Defender est un service IRC basé sur la sécurité des réseaux IRC ( UnrealIRCD )
Il permet d'ajouter une sécurité supplémentaire pour vérifier les users connectés au réseau
en demandant aux user un code de validation.
Il permet aux opérateurs de gérer efficacement un canal, tout en offrant aux utilisateurs des outils d'interaction et de décision collective.

# Fonctionnalités principales
    Commandes opérateurs complètes:
        Kick: Expulser un utilisateur du canal.
        Ban: Interdire définitivement l'accès au canal.
        Unban: Lever une interdiction.
        Op/Deop/Opall/Deopall: Attribuer ou retirer les droits d'opérateur.
        Halfop/Dehalfop: Attribuer ou retirer les droits
        Voice/Devoice/VoiceAll/DevoiceAll: Attribuer ou retirer les droits de voix.

    Système de quarantaine:
        Mise en quarantaine: Isoler temporairement un utilisateur dans un canal privé.
        Libération: Permettre à un utilisateur de quitter la quarantaine en entrant un code spécifique.

    Système de vote:
        Kick: Les utilisateurs peuvent voter pour expulser un membre du canal.
        Autres actions: Possibilité d'étendre le système de vote à d'autres actions (ban, etc.).

# Installation automatique sur une machine Debian/Ubuntu

    Prérequis:
        - Système d'exploitation Linux (Windows non supporté)
        - Un server UnrealIRCD corréctement configuré
        - Python version 3.10 ou supérieure
```bash
        # Bash
        $ git clone https://github.com/adator85/IRC_DEFENDER_MODULES.git
        # Renommer le fichier exemple_configuration.json en configuration.json
        # Configurer le fichier configuration.json
        $ python3 main.py
```
Si votre configuration est bonne, votre service est censé etre connecté a votre réseau IRC
Pour Les prochains lancement de defender vous devez utiliser la commande suivante:

```bash
    # Bash
    $ systemctl --user [start | stop | restart | status] defender
```
# Installation manuelle:
```bash
    # Bash
    $ git clone https://github.com/adator85/IRC_DEFENDER_MODULES.git
    $ cd IRC_DEFENDER_MODULES
    $ python3 -m venv .pyenv
    $ source .pyenv/bin/activate
    (pyenv)$ pip install sqlalchemy, psutil, requests, faker, unrealircd_rpc_py

    # Créer un service nommé "defender.service" 
    # pour votre service et placer le dans "/PATH/TO/USER/.config/systemd/user/"
    # Si le dossier n'existe pas il faut les créer
    $ sudo systemctl --user start defender
```
# Configuration
```
    SERVEUR (Serveur)
        * SERVEUR_IP: Adresse IP du serveur IRC à rejoindre. (default : 127.0.0.1)
        * SERVEUR_HOSTNAME: Nom d'hôte du serveur IRC à rejoindre (optionnel).
        * SERVEUR_LINK: Lien vers le serveur IRC (optionnel).
        * SERVEUR_PORT: Port de connexion au serveur IRC.
        * SERVEUR_PASSWORD: Mot de passe d'enregistrement du service sur le serveur IRC.
        SERVEUR_ID: Identifiant unique du service. (default : 19Z)
        SERVEUR_SSL: Active la connexion SSL sécurisée au serveur IRC (true/false) (default : false).

    SERVICE (Service)
        SERVICE_NAME: Nom du service IRC. (default : Defender)
        SERVICE_NICKNAME: Surnom utilisé par le service sur le serveur IRC. (default : Defender)
        SERVICE_REALNAME: Nom réel du service affiché sur le serveur IRC. (default : Defender Security)
        SERVICE_USERNAME: Nom d'utilisateur utilisé par le service pour se connecter au serveur IRC. (default : IRCSecurity)
        SERVICE_HOST: Nom d'hôte du service affiché sur le serveur IRC (optionnel). (default : defender.local.network)
        SERVICE_INFO: Description du service. (default : Defender Network IRC Service)
        SERVICE_CHANLOG: Canal utilisé pour la journalisation des actions du service. (default : #services)
        SERVICE_SMODES: Modes serveur appliqués aux canaux rejoints par le service. (default : +ioqBS)
        SERVICE_CMODES: Modes de canal appliqués aux canaux rejoints par le service. (default : ntsOP)
        SERVICE_UMODES: Modes utilisateur appliqués au service. (default : o)
        SERVICE_PREFIX: Caractère utilisé comme préfixe des commandes du service. (default : !)

    COMPTE (Compte)
        OWNER: Nom d'utilisateur possédant les droits d'administration du service. (default : admin)
        PASSWORD: Mot de passe de l'administrateur du service. (default : admin)

    CANAUX (Canaux)
        SALON_JAIL: Canal utilisé comme prison pour les utilisateurs sanctionnés. (default : #jail)
        SALON_JAIL_MODES: Modes appliqués au canal de prison. (default : sS)
        SALON_LIBERER: Canal utilisé pour la libération des utilisateurs sanctionnés. (default : #welcome)

    API (API)
        API_TIMEOUT: Durée maximale d'attente d'une réponse de l'API en secondes. (default : 2)

    SCANNER (Scanner)
        PORTS_TO_SCAN: Liste des ports à scanner pour détecter des serveurs potentiellement malveillants. (default : [])

    SÉCURITÉ (Sécurité)
        WHITELISTED_IP: Liste d'adresses IP autorisées à contourner certaines restrictions. (default : ['127.0.0.1'])
        GLINE_DURATION: Durée de bannissement temporaire d'un utilisateur en minutes. (default : "30")

    DEBUG (Debug)
        DEBUG_LEVEL: Niveau de verbosité des messages de debug (plus grand est le nombre, plus il y a d'informations). (default : 20) Pour une production

```
    Modification de la configuration

        Vous devez modifier le fichier configuration.json en remplaçant les valeurs par défaut avec vos propres informations. Assurez-vous de bien lire la description de chaque paramètre pour une configuration optimale du service.

## Exemple de configuration de base
```json
{
    "SERVEUR_IP": "IP.DE.TON.SERVER",
    "SERVEUR_HOSTNAME": "HOST.DE.TON.SERVER",
    "SERVEUR_LINK": "LINK.DE.TON.SERVER",
    "SERVEUR_PORT": 6901,
    "SERVEUR_PASSWORD": "MOT_DE_PASS_DE_TON_LINK",
    "SERVEUR_ID": "10Z",
    "SERVEUR_SSL": true,

    "SERVICE_NAME": "defender",
    "SERVICE_NICKNAME": "PyDefender",
    "SERVICE_REALNAME": "Python Defender Security",
    "SERVICE_USERNAME": "PyDefender",
    "SERVICE_HOST": "HOST.DE.TON.DEFENDER",

    "OWNER": "TON_NICK_NAME",
    "PASSWORD": "TON_PASSWORD"

}

```

## Exemple complet de configuration
```json
{
    "SERVEUR_IP": "YOUR.SERVER.IP",
    "SERVEUR_HOSTNAME": "YOUR.SERVER.HOST",
    "SERVEUR_LINK": "LINK.DE.TON.SERVER",
    "SERVEUR_PORT": 6901,
    "SERVEUR_PASSWORD": "YOUR_LINK_PASSWORD",
    "SERVEUR_ID": "10Z",
    "SERVEUR_SSL": true,

    "SERVICE_NAME": "defender",
    "SERVICE_NICKNAME": "PyDefender",
    "SERVICE_REALNAME": "Python Defender Security",
    "SERVICE_USERNAME": "PyDefender",
    "SERVICE_HOST": "HOST.DE.TON.DEFENDER",
    "SERVICE_INFO": "Network IRC Service",
    "SERVICE_CHANLOG": "#services",
    "SERVICE_SMODES": "+ioqBS",
    "SERVICE_CMODES": "ntsOP",
    "SERVICE_UMODES": "o",
    "SERVICE_PREFIX": "!",

    "OWNER": "TON_NICK_NAME",
    "PASSWORD": "TON_PASSWORD",

    "JSONRPC_URL": "https://your.domaine.com:8600/api",
    "JSONRPC_PATH_TO_SOCKET_FILE": "/PATH/TO/YOUR/IRCD/data/rpc.socket",
    "JSONRPC_METHOD": "socket",
    "JSONRPC_USER": "YOUR_RPC_USER",
    "JSONRPC_PASSWORD": "YOUR_RPC_PASSWORD",

    "SALON_JAIL": "#jail",
    "SALON_JAIL_MODES": "sS",
    "SALON_LIBERER": "#welcome",

    "CLONE_CHANNEL": "#clones",
    "CLONE_CMODES": "+nts",
    "CLONE_LOG_HOST_EXEMPT": ["HOST.TO.SKIP"],
    "CLONE_CHANNEL_PASSWORD": "YOUR_CHANNEL_PASSWORD",

    "API_TIMEOUT": 2,

    "PORTS_TO_SCAN": [3028, 8080, 1080, 1085, 4145, 9050],
    "WHITELISTED_IP": ["127.0.0.1"],
    "GLINE_DURATION": "30",

    "DEBUG_LEVEL": 20

}
```

# \\!/ Attention \\!/
Le mot de passe de l'administrateur et le mot de passe du service doivent être modifiés pour des raisons de sécurité.
Ne partagez pas vos informations de connexion au serveur IRC avec des tiers.
a votre premiere connexion vous devez tapez 
```
    /msg [NomDuService] auth [nickname] [password]
    -- Une fois identifié tapez la commande suivante
    /msg [NomDuService] editaccess [nickname] [Nouveau-Password] 5
```
# Unrealircd configuration
```
listen {
	ip *;
	port 6901;
	options { tls; serversonly; }
}

link LINK.DE.TON.SERVER
{

	incoming {
                mask *;
                bind-ip *;
                port 6901;
                //options { tls; };
        }

	outgoing {
                bind-ip *; /* ou une IP précise */
                hostname LINK.DE.TON.SERVER;
                port 6901;
                //options { tls; }
        }

	password "YOUR_LINK_PASSWORD";
	
        class servers;

}

ulines {
	LINK.DE.TON.SERVER;
}
```

# Extension:
    Le code est modulaire et conçu pour être facilement étendu. Vous pouvez ajouter de nouvelles commandes, de nouvelles fonctionnalités (mods/mod_test.py  est un exemple pour bien demarrer la création de son module).

# Contributions:
    Les contributions sont les bienvenues ! N'hésitez pas à ouvrir des issues ou des pull requests.

# Avertissement:
    Ce bot est fourni "tel quel" sans aucune garantie. Utilisez-le à vos risques et périls.