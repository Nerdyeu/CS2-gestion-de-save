import queue


class ThreadSafeUIMixin:
    """Permet aux threads de travail de mettre à jour l'UI Tkinter sans planter.

    Tkinter n'est PAS thread-safe : même `widget.after(...)` plante s'il est
    appelé depuis un autre thread (il enregistre une commande Tcl). La règle
    sûre : seul le thread principal touche aux widgets.

    Ici, les threads déposent une fonction via `post(fn)` dans une file ; un
    « videur » (`_drain_ui_queue`) tourne en boucle sur le thread principal
    (relancé par `after`, appelé depuis le thread principal) et exécute ces
    fonctions au bon endroit.
    """

    def _init_ui_queue(self, interval_ms=80):
        self._ui_queue = queue.Queue()
        self._ui_interval = interval_ms
        # Premier `after` appelé depuis le thread principal -> sûr.
        self.after(self._ui_interval, self._drain_ui_queue)

    def post(self, fn):
        """Demande l'exécution de `fn` sur le thread principal (appelable de partout)."""
        self._ui_queue.put(fn)

    def _drain_ui_queue(self):
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except Exception:
                    # Une MAJ d'UI ratée ne doit jamais tuer la boucle.
                    pass
        except queue.Empty:
            pass
        # On se replanifie tant que la fenêtre existe.
        try:
            self.after(self._ui_interval, self._drain_ui_queue)
        except Exception:
            pass
