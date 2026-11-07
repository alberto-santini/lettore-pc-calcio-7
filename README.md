# Lettore PC Calcio 7

Questo lettore può essere usato per estrarre programmaticamente informazioni sui calciatori, a partire dalla base di dati originale di PC Calcio 7 e da un file di salvataggio.
Consideratelo come una versione avanzata del "Direttore Tecnico".
L'estrattore produce un file `.csv` che può essere usato per ottenere informazioni molto precise sui calciatori.
Per esempio:
    * Quali calciatori hanno meno di 25 anni, una media di almeno 80, e uno stipendio di al piú 20 milioni di Lire?
    * Quali portieri hanno una media di almeno 86 e sono all'ultimo anno di contratto?
    * Chi sono i mediani spagnoli che giocano in Italia o in Francia, e guadagnano piú di 100 milioni di Lire?

## Funzionamento

Anche se molti parametri sono personalizzabili, questo codice è piú che altro per uso personale.
Io lo uso in questo modo:

* Ho una macchina virtuale UTM (host: macos, guest: Windows XP) con PC Calcio 7 installato in `C:\CALCIO7`.
* Ho una copia di `CALCIO7` sulla mia scrivania (`/Users/alberto/Desktop`).
* Dentro la mia copia di `CALCIO7` ho una cartella chiamata `editor`.
* Il codice è dentro questa cartella `editor`.

## Patch facoltative

Lo script `patch_promanag.py` applica alcune patch che evitano il blocco del gioco nei casi sequnti.

### Squadre duplicate nelle coppe

Una prima patch corregge il blocco che può verificarsi in ProManager dopo aver premuto **Continua** nella schermata **Fine della stagione**.
Il blocco si materializza soprattutto quando, per un errore, ci sono squadre duplicate che si qualificano per le coppe europee e la tua squadra ne viene cosí estromessa.
A volte le squadre classificate per la Coppa dei Campioni e la Coppa UEFA contengono errori.
Per esempio, le qualificate per la Coppa dei Campioni potrebbero essere "Inter, Milan, Milan, Roma", con il Milan ripetuto due volte.
Questo causa errori nella lista di squadre che si classificano per le coppe europee e la tua squadra potrebbe essere considerata come non classificata.
Se questo era il tuo obiettivo, viene considerato come non raggiunto, ma solo alla fine della stagione.
Quindi non vieni mai esonerato durante la stagione, ma il gioco ti esonera "virtualmente" all'ultimissimo turno della stagione in corso.
Nonappena inizia la stagione seguente del ProManager, quando dovresti scegliere tra le offerte delle squadra, il gioco va in blocco.
Con questa patch a `MANAGCAL.EXE`, il problema viene risolto.

### Blocco in Info Manager

A volte, andando su **Decisioni** e poi su **Info Manager**, il programma si blocca perché non riesce a leggere le informazioni su alcune partite storiche.
La patch evita il blocco e stampa una stringa vuota laddove dovrebbero andare le informazioni relative a partite che si sono "perse" nella storia del manager contenuta nel salvataggio.
