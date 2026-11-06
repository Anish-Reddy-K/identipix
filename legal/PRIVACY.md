# Privacy Policy

_Last updated: November 5, 2026_

Identipix helps event guests find the photos they appear in. This page explains, in plain language, what the software stores and what it does not.

## The short version

- Your selfie is used in memory to find matches, then thrown away. It is never saved or logged.
- We do not store photos. They stay in the organizer's Google Drive.
- We store a numeric "face fingerprint" for each face found in the event photos, so matching can be fast.
- Events are deleted automatically after 30 days, or earlier if the organizer deletes them.
- No accounts, no cookies, no analytics, no ads.

## What is stored

For each event, the organizer's Google Drive folder is read and these are saved:

| What | Why |
| --- | --- |
| Event name, folder ID, status, progress, dates | To run the event page |
| A secret admin link token | So only the organizer can manage the event |
| Photo file IDs and file names | To show matches and link back to Drive |
| One face fingerprint per face (128 numbers) | To match selfies. It is not an image. It is still treated as biometric data |
| The list of "Highlights" the organizer picked | To show them to every guest |

## What is not stored

- Photo files. Photos are read from Google Drive and not kept. Small and large previews pass through the server on their way to your browser and are not saved there. Your browser may cache them for a day.
- Selfies. A selfie is read into memory, turned into a fingerprint, compared, and discarded. It is never written to disk and never logged.
- Accounts, names, emails or cookies of guests.

## Your IP address

To limit abuse, the number of requests per IP address is counted in memory. It is not saved to the database and is lost when the server restarts. The server's own request logs may record standard details such as time, page and status.

## Other services involved

- **Google Drive** holds the photos. Opening or downloading a photo happens on Google, under Google's own privacy policy.
- **Cloudflare** carries traffic between you and the server (a tunnel), so it can see that traffic as it passes.
- Face detection and matching run on the server itself. No selfie or photo is sent to any AI service.

## How long we keep data

Events and their fingerprints are deleted automatically after 30 days, or immediately when the organizer deletes the event. Anyone running their own copy can change the 30 days.

## Your choices

- You do not have to take a selfie. Highlights and the "View all photos" link work without one.
- To have an event's data removed, ask the organizer to delete it, or write to us at the address below. Fingerprints are not linked to a name or account, so removal is done per event, not per person.
- If you do not want to appear in an event's photos, ask the organizer to remove them from the Drive folder.

## For organizers

You are responsible for having the right to share the photos and for telling guests that their selfie will be used to find their photos. A short sign at the event is enough, for example: "Photos here are found with face matching. Your selfie is processed in memory and never stored."

## Who runs it

The hosted service at identipix.com is run by Identipix in Waterloo, Canada, and this policy covers it. Identipix is also open source: if someone else runs their own copy, they are responsible for that copy's data, and this policy does not cover it.

## Contact

contact@identipix.com
